"""Kanıt ve rubrik: kanıt ekleme, itiraz ve kart hazırlama aynı yoldan yazar.

Kural ve LLM `app/agents/dogrulama/`'da; burada rubriğin iş kalemine yazılması.
Hata çevirisi (hız sınırı → 429) uçların işi: arka plan işi aynı hatayı yakalayıp
kalemi puansız bırakır. Commit çağıranın işi.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.dogrulama import LinkKontrolu, linki_kontrol_et, rubrik_puanla
from app.core.is_kalemi import is_kalemi_metni, kanit_bekliyor
from app.models.guven_skoru import GuvenSkoru
from app.models.referans_istegi import ReferansIstegi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler.dogrulama.referans import ucuncu_taraf_puani


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
        kanit_linki=cikti.kanit_linki,
        kontrol=kontrol,
        itiraz_notu=itiraz_notu,
    )

    if cikti.guven_skoru is None:
        cikti.guven_skoru = GuvenSkoru(
            kanit_orijinalligi=puan.kanit_orijinalligi,
            sonuc_olculebilirligi=puan.sonuc_olculebilirligi,
            rol_netligi=puan.rol_netligi,
            # Sıfırdan yazılıyor (ilk puan ya da iş değiştiği için sıfırlandı):
            # değişiklikten sonra gelmiş referans yanıtı varsa o sayılır.
            ucuncu_taraf_onayi=ucuncu_taraf_puani(cikti),
            gerekce_metni=puan.gerekce_metni,
        )
    else:
        cikti.guven_skoru.kanit_orijinalligi = puan.kanit_orijinalligi
        cikti.guven_skoru.sonuc_olculebilirligi = puan.sonuc_olculebilirligi
        cikti.guven_skoru.rol_netligi = puan.rol_netligi
        cikti.guven_skoru.gerekce_metni = puan.gerekce_metni


async def ciktiyi_puanla(cikti: SomutCikti) -> LinkKontrolu:
    """Linki sınar ve rubriği yazar (kart hazırlamanın kalem başına işi)."""
    kontrol = await linki_kontrol_et(cikti.kanit_linki)
    await rubrigi_yaz(cikti, kontrol)
    return kontrol


async def kanit_ekle(
    oturum: AsyncSession,
    cikti: SomutCikti,
    *,
    kanit_linki: str | None,
    kanit_turu: str | None,
    referans_email: str | None,
) -> LinkKontrolu:
    """Kanıtı kaydeder, erişilebilirliğini sınar, ön rubriği üretir; varsa referans ister."""
    if kanit_linki:
        cikti.kanit_linki = kanit_linki
    if kanit_turu:
        cikti.kanit_turu = kanit_turu

    kontrol = await ciktiyi_puanla(cikti)

    if referans_email:
        cikti.referans_istekleri.append(ReferansIstegi(referans_email=referans_email))

    await kanit_bekleyeni_guncelle(oturum, cikti.yetenek_karti_id)
    return kontrol


async def kanit_bekleyeni_guncelle(oturum: AsyncSession, yetenek_karti_id: uuid.UUID) -> None:
    """Kartın `kanit_bekleyen` bayrağını çıktılarla tutarlı tutar
    (kural: app/core/is_kalemi.kanit_bekliyor; onay ve düzenleme de onu kullanır)."""
    kart = await oturum.scalar(
        select(YetenekKarti)
        .options(
            selectinload(YetenekKarti.somut_ciktilar).selectinload(SomutCikti.referans_istekleri)
        )
        .where(YetenekKarti.id == yetenek_karti_id)
    )
    if kart is not None:
        kart.kanit_bekleyen = kanit_bekliyor(kart.somut_ciktilar)
