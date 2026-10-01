"""Kanıtın değerlendirilmesi: kanıt ekleme / kaldırma, değerlendirme, itiraz ve
kart hazırlama aynı yoldan yazar.

Parça ekleme ve kaldırmanın kuralı `parcalar.py`'de (tek kapı); burada parçanın
okunup rubriğin iş kalemine yazılması. Kural ve LLM `app/agents/dogrulama/`'da.
Hata çevirisi (hız sınırı → 429) uçların işi: arka plan işi aynı hatayı
yakalayıp kalemi değerlendirilmemiş bırakır. Commit çağıranın işi.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.dogrulama import LinkKontrolu, linki_kontrol_et, rubrik_puanla
from app.core.is_kalemi import is_kalemi_metni, kanit_bekliyor
from app.models.guven_skoru import GuvenSkoru
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler.dogrulama.parcalar import birincil_link, link_parcasi_ekle, parca_sil
from app.servisler.dogrulama.referans import ucuncu_taraf_puani


class DegerlendirilecekKanitYok(LookupError):
    """Çalışmanın değerlendirilecek bir kanıt linki yok (uçta 409)."""


async def rubrigi_yaz(
    cikti: SomutCikti, kontrol: LinkKontrolu, itiraz_notu: str | None = None
) -> None:
    """Ön rubriği üretip kaydeder; üçüncü taraf onayı korunur.

    LLM hataları (hız sınırı, arıza) çağırana çıkar.
    """
    puan = await rubrik_puanla(
        baslik=cikti.baslik,
        # Sonuç ve rol ayrı alanlarda; rubrik işi tek metin olarak okur.
        aciklama=is_kalemi_metni(cikti),
        kanit_linki=birincil_link(cikti),
        kontrol=kontrol,
        itiraz_notu=itiraz_notu,
    )

    simdi = dt.datetime.now(dt.UTC)
    if cikti.guven_skoru is None:
        cikti.guven_skoru = GuvenSkoru(
            kanit_orijinalligi=puan.kanit_orijinalligi,
            sonuc_olculebilirligi=puan.sonuc_olculebilirligi,
            rol_netligi=puan.rol_netligi,
            # Sıfırdan yazılıyor (ilk puan ya da iş değiştiği için sıfırlandı):
            # değişiklikten sonra gelmiş referans yanıtı varsa o sayılır.
            ucuncu_taraf_onayi=ucuncu_taraf_puani(cikti),
            gerekce_metni=puan.gerekce_metni,
            degerlendirme_tarihi=simdi,
        )
    else:
        cikti.guven_skoru.kanit_orijinalligi = puan.kanit_orijinalligi
        cikti.guven_skoru.sonuc_olculebilirligi = puan.sonuc_olculebilirligi
        cikti.guven_skoru.rol_netligi = puan.rol_netligi
        cikti.guven_skoru.gerekce_metni = puan.gerekce_metni
        cikti.guven_skoru.degerlendirme_tarihi = simdi


async def degerlendir(cikti: SomutCikti, itiraz_notu: str | None = None) -> LinkKontrolu:
    """Birincil linki okur ve rubriği yazar (uçların ve kart hazırlamanın ortak işi).

    `cikti.kanit_parcalari`, `guven_skoru` ve `referans_istekleri` yüklenmiş olmalı.
    """
    link = birincil_link(cikti)
    if link is None:
        raise DegerlendirilecekKanitYok("Değerlendirilecek bir kanıt linki yok.")
    kontrol = await linki_kontrol_et(link)
    await rubrigi_yaz(cikti, kontrol, itiraz_notu=itiraz_notu)
    return kontrol


async def ciktiyi_puanla(cikti: SomutCikti) -> LinkKontrolu:
    """Kart hazırlamanın kalem başına işi: çalışmayı değerlendirir."""
    return await degerlendir(cikti)


async def kanit_linki_ekle(cikti: SomutCikti, url: str) -> LinkKontrolu:
    """Link parçası ekler ve çalışmayı hemen yeniden değerlendirir."""
    link_parcasi_ekle(cikti, url)
    return await degerlendir(cikti)


async def kanit_parcasini_sil(cikti: SomutCikti, parca_id: uuid.UUID) -> LinkKontrolu | None:
    """Parçayı kaldırır; başka link kaldıysa onunla yeniden değerlendirir.

    Hiç link kalmadıysa göstergenin değerlendirme kısmı boş ("—") kalır,
    Referans korunur: kanıtsız çalışma ceza almaz, bonus da almaz.
    """
    parca_sil(cikti, parca_id)
    if birincil_link(cikti) is None:
        return None
    return await degerlendir(cikti)


async def kanit_bekleyeni_guncelle(oturum: AsyncSession, yetenek_karti_id: uuid.UUID) -> bool:
    """Kartın `kanit_bekleyen` bayrağını çıktılarla tutarlı tutar; yeni değeri döner
    (kural: app/core/is_kalemi.kanit_bekliyor; onay ve düzenleme de onu kullanır)."""
    kart = await oturum.scalar(
        select(YetenekKarti)
        .options(
            selectinload(YetenekKarti.somut_ciktilar).selectinload(SomutCikti.referans_istekleri),
            selectinload(YetenekKarti.somut_ciktilar).selectinload(SomutCikti.kanit_parcalari),
        )
        .where(YetenekKarti.id == yetenek_karti_id)
    )
    if kart is None:
        return False
    kart.kanit_bekleyen = kanit_bekliyor(kart.somut_ciktilar)
    return kart.kanit_bekleyen
