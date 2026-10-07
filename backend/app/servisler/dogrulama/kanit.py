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
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.dogrulama.capalar import KimlikDurumu, dosya_seviyesi
from app.agents.dogrulama.cekirdek import (
    KURAL_SURUMU,
    DegerlendirmeGirdisi,
    DegerlendirmeSonucu,
    kalemi_degerlendir,
    ozet_hesapla,
)
from app.agents.dogrulama.cikarim import cikar
from app.agents.dogrulama.hesap_sahipligi import BagliHesapBilgisi
from app.agents.dogrulama.kimlik import ad_kilitli
from app.agents.dogrulama.kurallar import OkunanKanit
from app.agents.dogrulama.okuma import dosya_okunusu, kanit_oku
from app.core.is_kalemi import kanit_bekliyor
from app.core.kanit_okuma.belge import ParcaTuru
from app.core.llm import kullanim_topla
from app.models.gozlem import KAYNAK_DEGERLENDIRME
from app.models.guven_skoru import GuvenSkoru
from app.models.kanit_parcasi import KanitParcasi
from app.models.kullanici import Kullanici
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_kaniti import YetenekKaniti
from app.models.yetenek_karti import YetenekKarti
from app.servisler import gozlem
from app.servisler.dogrulama import isaretler
from app.servisler.dogrulama.parcalar import link_parcasi_ekle, okunabilir_mi, parca_sil
from app.servisler.dogrulama.referans import referans_destegi_hesapla, ucuncu_taraf_puani
from app.servisler.dogrulama.sorgular import bagli_hesap_bilgileri


@dataclass(frozen=True)
class Hazirlik:
    """Değerlendirmenin girdisi: parçaların okunuşu ve iddia. Model henüz çağrılmadı.

    `parcalar` ve `okunanlar` aynı sırada: okunuş parçaya geri yazılır.
    """

    parcalar: tuple[KanitParcasi, ...]
    okunanlar: tuple[OkunanKanit, ...]
    girdi: DegerlendirmeGirdisi
    # Kalemin sahibi (kötüye kullanım sinyallerinde kendi parçaları ayrılır)
    kullanici_id: uuid.UUID | None = None

    @property
    def okunan(self) -> OkunanKanit | None:
        """Son eklenen parçanın okunuşu (kanıt ekleyen uç onu bildirir)."""
        return self.okunanlar[-1] if self.okunanlar else None

    @property
    def ozet(self) -> str:
        return ozet_hesapla(self.girdi, self.okunanlar)


async def hazirla(
    oturum: AsyncSession, cikti: SomutCikti, itiraz_notu: str | None = None
) -> Hazirlik:
    """Her kanıt parçasını okur ve iddiayı toplar (ağ ve embedding var, model yok)."""
    kart = await oturum.scalar(
        select(YetenekKarti)
        .options(selectinload(YetenekKarti.kullanici).selectinload(Kullanici.hesap))
        .where(YetenekKarti.id == cikti.yetenek_karti_id)
    )
    girdi = _girdi(kart, cikti, itiraz_notu)
    kullanici_id = kart.kullanici_id if kart else None
    parcalar = tuple(p for p in cikti.kanit_parcalari if okunabilir_mi(p))
    if not parcalar:
        return Hazirlik((), (), girdi, kullanici_id)
    bagli = await bagli_hesap_bilgileri(oturum, kart.kullanici_id) if kart else ()
    sorgular = _iddia_sorgulari(girdi)
    kimlik = _kimlik_durumu(kart)
    olcumler = [await _olcumlu_oku(p, sorgular, bagli, kimlik) for p in parcalar]
    okunanlar = tuple(okunan for okunan, _ in olcumler)
    hazirlik = Hazirlik(parcalar, okunanlar, girdi, kullanici_id)
    _okumalari_gozle(oturum, hazirlik, [ms for _, ms in olcumler])
    return hazirlik


async def _olcumlu_oku(
    parca: KanitParcasi,
    sorgular: list[str],
    bagli: tuple[BagliHesapBilgisi, ...],
    kimlik: KimlikDurumu,
) -> tuple[OkunanKanit, int]:
    baslangic = time.perf_counter()
    okunan = await _parcayi_oku(parca, sorgular, bagli, kimlik)
    return okunan, round((time.perf_counter() - baslangic) * 1000)


def _okumalari_gozle(oturum: AsyncSession, hazirlik: Hazirlik, sureler_ms: list[int]) -> None:
    """Her link okuması gözlem kaydına yazılır (docs/dogrulama.md § 10.3); dosya yüklenirken
    okunmuştur."""
    ozet = hazirlik.ozet
    for parca, okunan, sure_ms in zip(
        hazirlik.parcalar, hazirlik.okunanlar, sureler_ms, strict=True
    ):
        if parca.tur == ParcaTuru.LINK.value:
            gozlem.kanit_okuma_ekle(
                oturum,
                kaynak=KAYNAK_DEGERLENDIRME,
                platform=okunan.platform,
                okuyucu=okunan.okuyucu,
                erisim=okunan.erisim.value,
                seviye=okunan.seviye.value,
                sure_ms=sure_ms,
                girdi_ozeti=ozet,
            )


def _kimlik_durumu(kart: YetenekKarti | None) -> KimlikDurumu:
    hesap = kart.kullanici.hesap if kart and kart.kullanici else None
    if hesap is None:
        return KimlikDurumu()
    return KimlikDurumu(
        eposta_dogrulandi=hesap.eposta_dogrulandi_tarihi is not None,
        ad_kilitli=ad_kilitli(hesap.eposta_dogrulandi_tarihi),
    )


async def _parcayi_oku(
    parca: KanitParcasi,
    sorgular: list[str],
    bagli: tuple[BagliHesapBilgisi, ...],
    kimlik: KimlikDurumu,
) -> OkunanKanit:
    if parca.tur == ParcaTuru.LINK.value:
        return await kanit_oku(parca.url, sorgular, bagli_hesaplar=bagli)
    return await dosya_okunusu(
        tur=parca.tur,
        dosya_adi=parca.dosya_adi,
        tam_metin=parca.tam_metin,
        betim=(parca.belge or {}).get("betim"),
        capa=dosya_seviyesi(parca.belge or {}, kimlik),
        iddia_sorgulari=sorgular,
    )


def _iddia_sorgulari(girdi: DegerlendirmeGirdisi) -> list[str]:
    """Uzun kanıt metninde parça seçimi için iddianın üç yüzü (iş, sonuç, pay)."""
    return [f"{girdi.baslik} {girdi.aciklama or ''}", girdi.sonuc or "", girdi.pay or ""]


def onbellekte_mi(cikti: SomutCikti, hazirlik: Hazirlik) -> bool:
    """Aynı girdi daha önce değerlendirildiyse önceki sonuç geçerli."""
    skor = cikti.guven_skoru
    return (
        skor is not None
        and skor.degerlendirme_tarihi is not None
        and skor.girdi_ozeti == hazirlik.ozet
    )


async def uygula(oturum: AsyncSession, cikti: SomutCikti, hazirlik: Hazirlik) -> None:
    """Modeli çağırır, kuralla puanlar, göstergeyi yazar ve kötüye kullanım
    sinyallerini inceleme kuyruğuna bırakır (puanı değiştirmezler, İ1)."""
    baslangic = time.perf_counter()
    with kullanim_topla() as kullanim:
        sonuc = await kalemi_degerlendir(hazirlik.girdi, hazirlik.okunanlar, cikar)
    gozlem.degerlendirme_ekle(
        oturum,
        girdi_ozeti=sonuc.girdi_ozeti,
        parca_sayisi=len(hazirlik.parcalar),
        sure_ms=round((time.perf_counter() - baslangic) * 1000),
        model_cagrisi=kullanim.cagri,
        girdi_token=kullanim.girdi_token,
        cikti_token=kullanim.cikti_token,
    )
    _sonucu_yaz(cikti, sonuc, hazirlik)
    await _yetenek_kanitlarini_yaz(oturum, cikti, sonuc, hazirlik)
    if hazirlik.kullanici_id is not None:
        await oturum.flush()  # yeni parçaların kimliği sinyallere yazılır
        await isaretler.degerlendirme_isaretleri(
            oturum, cikti, hazirlik.kullanici_id, hazirlik.parcalar, sonuc.parca_celiskileri
        )


async def degerlendir(
    oturum: AsyncSession, cikti: SomutCikti, itiraz_notu: str | None = None
) -> OkunanKanit | None:
    """Çalışmayı değerlendirir ve göstergeyi yazar. Döner: son eklenen parçanın okunuşu.

    Linksiz çalışma da değerlendirilir (docs/dogrulama.md § 17, Karar 10): Sonuç ve
    Rol beyan tavanıyla, Kanıt "—". Aynı girdi (iddia, kanıt okunuşu, itiraz notu,
    kural sürümü) için önceki sonuç kullanılır, model çağrılmaz: itirazla zar atılamaz.
    `cikti.kanit_parcalari`, `guven_skoru` ve `referans_istekleri` yüklenmiş olmalı.
    """
    hazirlik = await hazirla(oturum, cikti, itiraz_notu)
    if not onbellekte_mi(cikti, hazirlik):
        await uygula(oturum, cikti, hazirlik)
    return hazirlik.okunan


async def ciktiyi_puanla(oturum: AsyncSession, cikti: SomutCikti) -> OkunanKanit | None:
    """Kart hazırlamanın kalem başına işi: çalışmayı değerlendirir."""
    return await degerlendir(oturum, cikti)


async def kanit_linki_ekle(oturum: AsyncSession, cikti: SomutCikti, url: str) -> OkunanKanit | None:
    """Link parçası ekler ve çalışmayı hemen yeniden değerlendirir."""
    link_parcasi_ekle(cikti, url)
    return await degerlendir(oturum, cikti)


async def kanit_parcasini_sil(
    oturum: AsyncSession, cikti: SomutCikti, parca_id: uuid.UUID
) -> OkunanKanit | None:
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


def _girdi(
    kart: YetenekKarti | None, cikti: SomutCikti, itiraz_notu: str | None
) -> DegerlendirmeGirdisi:
    destek = referans_destegi_hesapla(cikti)
    return DegerlendirmeGirdisi(
        baslik=cikti.baslik,
        iddia_sahibi=kart.kullanici.ad if kart else None,
        aciklama=cikti.aciklama,
        sonuc=cikti.olculebilir_sonuc,
        pay=cikti.kendi_rolu,
        yetenekler=tuple(kart.araclar_teknolojiler or ()) if kart else (),
        itiraz_notu=itiraz_notu,
        # Güncel bir referansın ilgili soruya "evet"i bağımsız destektir (docs/dogrulama.md § 7).
        # Eski 1-5 yanıt soruya özgü olmadığı için destek sayılmaz.
        referans_sonuc_evet=destek.sonuc,
        referans_pay_evet=destek.pay,
    )


def _sonucu_yaz(cikti: SomutCikti, sonuc: DegerlendirmeSonucu, hazirlik: Hazirlik) -> None:
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

    for parca, okunan, kalem_isaretleri in zip(
        hazirlik.parcalar, hazirlik.okunanlar, sonuc.parca_isaretleri, strict=True
    ):
        parca.erisim = okunan.erisim.value
        parca.seviye = okunan.seviye.value
        parca.sahiplik_kaynagi = okunan.sahiplik_kaynagi.value
        parca.platform = okunan.platform
        parca.okuma_tarihi = simdi
        parca.isaretler = list(kalem_isaretleri)


async def _yetenek_kanitlarini_yaz(
    oturum: AsyncSession, cikti: SomutCikti, sonuc: DegerlendirmeSonucu, hazirlik: Hazirlik
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
    if any(p.id is None for p in hazirlik.parcalar):
        await oturum.flush()  # yeni eklenen parçanın kimliği veritabanında atanır
    for kanit in sonuc.yetenek_kanitlari:
        parca = hazirlik.parcalar[kanit.parca] if kanit.parca is not None else None
        kaynak = parca.id if parca else None
        seviye = hazirlik.okunanlar[kanit.parca].seviye.value if parca else None
        kayit = mevcut.get(kanit.yetenek)
        if kayit is None:
            oturum.add(
                YetenekKaniti(
                    kart_id=cikti.yetenek_karti_id,
                    yetenek=kanit.yetenek,
                    en_guclu_puan=kanit.puan,
                    kaynak_parca_id=kaynak,
                    seviye=seviye,
                )
            )
        elif kanit.puan > kayit.en_guclu_puan:
            kayit.en_guclu_puan = kanit.puan
            kayit.kaynak_parca_id = kaynak
            kayit.seviye = seviye
