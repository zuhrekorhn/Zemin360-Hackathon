"""Kanıtın değerlendirilmesi: kanıt ekleme / kaldırma, değerlendirme, itiraz ve kart
hazırlama aynı yoldan yazar.

Parça ekleme ve kaldırmanın kuralı `parcalar.py`'de (tek kapı); puanlama
çekirdekte (`app/agents/dogrulama/cekirdek.py`: model gerçek çıkarır, kural
puanlar, şablon anlatır). Burada okunuşun ve sonucun modele yazılması.
Hata çevirisi (hız sınırı → 429) uçların işi: arka plan işi aynı hatayı
yakalayıp kalemi değerlendirilmemiş bırakır. Commit çağıranın işi.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.dogrulama.cekirdek import (
    KURAL_SURUMU,
    DegerlendirmeGirdisi,
    DegerlendirmeSonucu,
    kalemi_degerlendir,
    ozet_hesapla,
)
from app.agents.dogrulama.cikarim import cikar
from app.agents.dogrulama.kurallar import OkunanKanit
from app.agents.dogrulama.link_kontrolu import LinkKontrolu, linki_kontrol_et, okunan_kanit
from app.core.is_kalemi import kanit_bekliyor
from app.models.guven_skoru import GuvenSkoru
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_kaniti import YetenekKaniti
from app.models.yetenek_karti import YetenekKarti
from app.servisler.dogrulama.parcalar import birincil_link, link_parcasi_ekle, parca_sil
from app.servisler.dogrulama.referans import ucuncu_taraf_puani


@dataclass(frozen=True)
class Hazirlik:
    """Değerlendirmenin girdisi: kanıtın okunuşu ve iddia. Model henüz çağrılmadı."""

    kontrol: LinkKontrolu | None
    okunan: OkunanKanit | None
    girdi: DegerlendirmeGirdisi

    @property
    def ozet(self) -> str:
        return ozet_hesapla(self.girdi, self.okunan)


async def hazirla(
    oturum: AsyncSession, cikti: SomutCikti, itiraz_notu: str | None = None
) -> Hazirlik:
    """Birincil linki okur ve iddiayı toplar (ağ var, model yok)."""
    link = birincil_link(cikti)
    kontrol = await linki_kontrol_et(link) if link else None
    okunan = okunan_kanit(kontrol, link) if kontrol else None
    return Hazirlik(kontrol, okunan, await _girdi(oturum, cikti, itiraz_notu))


def onbellekte_mi(cikti: SomutCikti, hazirlik: Hazirlik) -> bool:
    """Aynı girdi daha önce değerlendirildiyse önceki sonuç geçerli (bulgu 15)."""
    skor = cikti.guven_skoru
    return (
        skor is not None
        and skor.degerlendirme_tarihi is not None
        and skor.girdi_ozeti == hazirlik.ozet
    )


async def uygula(oturum: AsyncSession, cikti: SomutCikti, hazirlik: Hazirlik) -> None:
    """Modeli çağırır, kuralla puanlar ve göstergeyi yazar."""
    sonuc = await kalemi_degerlendir(hazirlik.girdi, hazirlik.okunan, cikar)
    _sonucu_yaz(cikti, sonuc, hazirlik.okunan)
    await _yetenek_kanitlarini_yaz(oturum, cikti, sonuc)


async def degerlendir(
    oturum: AsyncSession, cikti: SomutCikti, itiraz_notu: str | None = None
) -> LinkKontrolu | None:
    """Çalışmayı değerlendirir ve göstergeyi yazar. Döner: link okunduysa okunuşu.

    Linksiz çalışma da değerlendirilir (karar 10): Sonuç ve Rol beyan tavanıyla,
    Kanıt "—". Aynı girdi (iddia, kanıt okunuşu, itiraz notu, kural sürümü) için
    önceki sonuç kullanılır, model çağrılmaz: itirazla zar atılamaz (bulgu 15).
    `cikti.kanit_parcalari`, `guven_skoru` ve `referans_istekleri` yüklenmiş olmalı.
    """
    hazirlik = await hazirla(oturum, cikti, itiraz_notu)
    if not onbellekte_mi(cikti, hazirlik):
        await uygula(oturum, cikti, hazirlik)
    return hazirlik.kontrol


async def ciktiyi_puanla(oturum: AsyncSession, cikti: SomutCikti) -> LinkKontrolu | None:
    """Kart hazırlamanın kalem başına işi: çalışmayı değerlendirir."""
    return await degerlendir(oturum, cikti)


async def kanit_linki_ekle(
    oturum: AsyncSession, cikti: SomutCikti, url: str
) -> LinkKontrolu | None:
    """Link parçası ekler ve çalışmayı hemen yeniden değerlendirir."""
    link_parcasi_ekle(cikti, url)
    return await degerlendir(oturum, cikti)


async def kanit_parcasini_sil(
    oturum: AsyncSession, cikti: SomutCikti, parca_id: uuid.UUID
) -> LinkKontrolu | None:
    """Parçayı kaldırır ve kalan kanıtla (yoksa yalnızca iddiayla) yeniden değerlendirir."""
    parca_sil(cikti, parca_id)
    return await degerlendir(oturum, cikti)


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


# --- Yardımcılar -------------------------------------------------------------------------


async def _girdi(
    oturum: AsyncSession, cikti: SomutCikti, itiraz_notu: str | None
) -> DegerlendirmeGirdisi:
    kart = await oturum.get(YetenekKarti, cikti.yetenek_karti_id)
    return DegerlendirmeGirdisi(
        baslik=cikti.baslik,
        aciklama=cikti.aciklama,
        sonuc=cikti.olculebilir_sonuc,
        pay=cikti.kendi_rolu,
        yetenekler=tuple(kart.araclar_teknolojiler or ()) if kart else (),
        itiraz_notu=itiraz_notu,
        # Referansın yapılandırılmış yanıtları adım 7'de; eski 1-5 yanıt soruya
        # özgü olmadığı için Sonuç ve Rol'e bağımsız destek sayılmaz.
    )


def _sonucu_yaz(cikti: SomutCikti, sonuc: DegerlendirmeSonucu, okunan: OkunanKanit | None) -> None:
    simdi = dt.datetime.now(dt.UTC)
    if cikti.guven_skoru is None:
        # Sıfırdan yazılıyor: değişiklikten sonra gelmiş referans yanıtı varsa o sayılır.
        cikti.guven_skoru = GuvenSkoru(ucuncu_taraf_onayi=ucuncu_taraf_puani(cikti))
    skor = cikti.guven_skoru
    skor.kanit_orijinalligi = sonuc.puanlar.kanit
    skor.sonuc_olculebilirligi = sonuc.puanlar.sonuc
    skor.rol_netligi = sonuc.puanlar.rol
    skor.gerekce_metni = sonuc.not_metni
    skor.girdi_ozeti = sonuc.girdi_ozeti
    skor.kural_surumu = KURAL_SURUMU
    skor.kanit_ozeti = {**sonuc.kanit_ozeti, "destekler": list(sonuc.destekler)}
    skor.degerlendirme_tarihi = simdi

    parca = next((p for p in cikti.kanit_parcalari if p.url == birincil_link(cikti)), None)
    if parca is not None and okunan is not None:
        parca.erisim = okunan.erisim.value
        parca.seviye = okunan.seviye.value
        parca.okuma_tarihi = simdi
        parca.isaretler = list(sonuc.isaretler)


async def _yetenek_kanitlarini_yaz(
    oturum: AsyncSession, cikti: SomutCikti, sonuc: DegerlendirmeSonucu
) -> None:
    """Yetenek başına en güçlü kanıt tutulur (yalnızca yükselir)."""
    if not sonuc.yetenek_kanitlari:
        return
    mevcut = {
        k.yetenek: k
        for k in await oturum.scalars(
            select(YetenekKaniti).where(YetenekKaniti.kart_id == cikti.yetenek_karti_id)
        )
    }
    parca = next((p for p in cikti.kanit_parcalari if p.url == birincil_link(cikti)), None)
    if parca is not None and parca.id is None:
        await oturum.flush()  # yeni eklenen parçanın kimliği veritabanında atanır
    seviye = sonuc.kanit_ozeti.get("seviye")
    for kanit in sonuc.yetenek_kanitlari:
        kayit = mevcut.get(kanit.yetenek)
        if kayit is None:
            oturum.add(
                YetenekKaniti(
                    kart_id=cikti.yetenek_karti_id,
                    yetenek=kanit.yetenek,
                    en_guclu_puan=kanit.puan,
                    kaynak_parca_id=parca.id if parca else None,
                    seviye=seviye,
                )
            )
        elif kanit.puan > kayit.en_guclu_puan:
            kayit.en_guclu_puan = kanit.puan
            kayit.kaynak_parca_id = parca.id if parca else None
            kayit.seviye = seviye
