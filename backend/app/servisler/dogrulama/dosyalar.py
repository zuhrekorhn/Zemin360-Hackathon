"""Dosya ve görsel kanıtının orkestrasyonu (plan § 4): sınırlar → yükleme hattı → içerik
okuma → çapa doğrulaması → depo → tek kapıdan parça → değerlendirme.

İçerik yükleme anında bir kez okunur ve maskelenmiş olarak saklanır (`tam_metin`,
`gorsel_metni`, `belge["betim"]`); değerlendirme ve itiraz dosyayı yeniden
indirmez, modele yeniden okutmaz.
  - PDF: önce metin katmanı (`pypdf`); yoksa ya da sayfa başına çok azsa model okur.
  - Görsel: model görülen metni ve betimi yazar (iki adımlı okumanın ilk adımı).

Depo ve virüs tarayıcı kurulum noktasından gelir (`core/dis_servisler/kurulum.py`).
Dosyanın depodan silinmesi commit'ten SONRA yapılır (arka planda, çağıranın işi):
işlem geri alınırsa satır durur, dosyası da durmalı. Ters yönde (dosya kondu,
işlem düştü) depoda sahipsiz bir dosya kalabilir; zararsızdır, kimse adresini almaz.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dogrulama.dosya_cikarimi import dosyayi_oku
from app.agents.dogrulama.kurallar import OkunanKanit
from app.core.config import get_settings
from app.core.dis_servisler import kurulum
from app.core.dosya_hatti import DosyaReddedildi, HazirDosya, dosyayi_hazirla, gorunen_ad
from app.core.kanit_okuma.belge import ParcaTuru
from app.core.kanit_okuma.maskeleme import maskele
from app.core.kanit_okuma.pdf import model_okumali_mi, pdf_metni
from app.models.hesap import Hesap
from app.models.kanit_parcasi import KanitParcasi
from app.models.kullanici import Kullanici
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler.dogrulama.capalar import CapaGirdisi, capalari_dogrula, edevlet, tekillik
from app.servisler.dogrulama.kanit import degerlendir
from app.servisler.dogrulama.parcalar import (
    DOSYA_TURLERI,
    KanitBulunamadi,
    dosya_eklenebilir_mi,
    dosya_parcasi_ekle,
    parca_bul,
)

logger = logging.getLogger("zemin360.dosyalar")


@dataclass(frozen=True)
class DosyaIcerigi:
    # Alıntı kaynağı: belgede yazan metin (maskelenmiş)
    tam_metin: str
    # Modelin gördüğü metin; model okumadıysa None
    gorsel_metni: str | None
    betim: str | None
    sayfa_sayisi: int | None
    okuyan: str  # "metin_katmani" | "model"


async def icerigi_oku(hazir: HazirDosya) -> DosyaIcerigi:
    """Model hatası (hız sınırı, sağlayıcı) çağırana çıkar: yükleme düşer, genç yeniden dener."""
    if hazir.parca_turu is ParcaTuru.DOSYA:
        metin, sayfa = pdf_metni(hazir.veri)
        if not model_okumali_mi(metin, sayfa):
            return DosyaIcerigi(maskele(metin), None, None, sayfa, "metin_katmani")
    else:
        sayfa = None
    okunus = await dosyayi_oku(hazir.veri, hazir.icerik_turu)
    gorulen = maskele(okunus.gorsel_metni.strip())
    return DosyaIcerigi(gorulen, gorulen, okunus.betim.strip() or None, sayfa, "model")


async def _capa_girdisi(
    oturum: AsyncSession, kullanici_id: uuid.UUID, hazir: HazirDosya, icerik: DosyaIcerigi
) -> CapaGirdisi:
    kullanici = await oturum.get(Kullanici, kullanici_id)
    hesap = await oturum.get(Hesap, kullanici.hesap_id) if kullanici.hesap_id else None
    return CapaGirdisi(
        ham=hazir.ham,
        icerik_turu=hazir.icerik_turu,
        metin=icerik.tam_metin,
        on_bilgi=hazir.on_bilgi,
        ad=kullanici.ad,
        eposta=hesap.email if hesap else kullanici.email,
    )


async def gunluk_yukleme_sayisi(oturum: AsyncSession, kullanici_id: uuid.UUID) -> int:
    """Son 24 saatte bu gencin yüklediği dosya sayısı (silinenler sayılmaz)."""
    sinir = dt.datetime.now(dt.UTC) - dt.timedelta(days=1)
    return await oturum.scalar(
        select(func.count(KanitParcasi.id))
        .join(SomutCikti, SomutCikti.id == KanitParcasi.somut_cikti_id)
        .join(YetenekKarti, YetenekKarti.id == SomutCikti.yetenek_karti_id)
        .where(
            YetenekKarti.kullanici_id == kullanici_id,
            KanitParcasi.tur.in_(DOSYA_TURLERI),
            KanitParcasi.olusturma_tarihi >= sinir,
        )
    )


async def dosya_ekle(
    oturum: AsyncSession,
    cikti: SomutCikti,
    kullanici_id: uuid.UUID,
    ham: bytes,
    ham_ad: str | None,
) -> OkunanKanit | None:
    """Dosyayı güvenli hale getirir, depoya koyar, parça olarak ekler ve çalışmayı
    değerlendirir. Reddedilen dosya için `DosyaReddedildi` / `DosyaSiniri` (422),
    aynı dosya için `KanitZatenVar` (409), depo kapalıysa `DepoKapali` (503)."""
    dosya_eklenebilir_mi(cikti)  # sınır doluysa dosya hiç işlenmez
    if await gunluk_yukleme_sayisi(oturum, kullanici_id) >= get_settings().gunluk_dosya_siniri:
        raise DosyaReddedildi("Bugünlük dosya yükleme sınırına ulaştın; yarın yeniden dene.")
    hazir = await dosyayi_hazirla(ham, kurulum.virus_tarayici())
    dosya_eklenebilir_mi(cikti, hazir.ozet)  # model ve depodan önce
    icerik = await icerigi_oku(hazir)
    capalar = await capalari_dogrula(await _capa_girdisi(oturum, kullanici_id, hazir, icerik))
    anahtar = f"kanit/{uuid.uuid4().hex}"
    belge = {
        "dosya": {
            "ad": gorunen_ad(ham_ad, hazir.icerik_turu),
            "icerik_turu": hazir.icerik_turu,
            "boyut": len(hazir.veri),
            "tarama": hazir.tarama.value,
            "sayfa": icerik.sayfa_sayisi,
            "okuyan": icerik.okuyan,
        },
        **({"betim": icerik.betim} if icerik.betim else {}),
        **hazir.on_bilgi,
        "capalar": capalar,
    }
    depo = kurulum.depo()
    await depo.koy(anahtar, hazir.veri, hazir.icerik_turu)
    parca = dosya_parcasi_ekle(
        cikti,
        tur=hazir.parca_turu,
        dosya_anahtari=anahtar,
        dosya_ozeti=hazir.ozet,
        belge=belge,
        tam_metin=icerik.tam_metin,
        gorsel_metni=icerik.gorsel_metni,
    )
    try:
        await edevlet.inceleme_ac(oturum, parca, cikti, kullanici_id)
        await tekillik.belge_tekilligi(oturum, parca, cikti, kullanici_id)
        return await degerlendir(oturum, cikti)
    except Exception:
        await depo.sil(anahtar)  # işlem geri alınacak: dosya sahipsiz kalmasın
        raise


def dosya_bilgisi(parca: KanitParcasi) -> dict:
    return (parca.belge or {}).get("dosya", {})


async def indirme_adresi(cikti: SomutCikti, parca_id: uuid.UUID) -> str:
    """Kısa ömürlü imzalı adres; yetki denetimi çağıranın işi."""
    parca = parca_bul(cikti, parca_id)
    if not parca.dosya_anahtari:
        raise KanitBulunamadi(parca_id)
    bilgi = dosya_bilgisi(parca)
    return await kurulum.depo().imzali_adres(
        parca.dosya_anahtari,
        dosya_adi=bilgi.get("ad", "kanit"),
        icerik_turu=bilgi.get("icerik_turu", "application/octet-stream"),
    )


def gorunurlugu_degistir(cikti: SomutCikti, parca_id: uuid.UUID, gorunur: bool) -> KanitParcasi:
    """Genç dosyayı firmaların görüp göremeyeceğini seçer (plan § 4.4). Gösterge değişmez."""
    parca = parca_bul(cikti, parca_id)
    if not parca.dosya_anahtari:
        raise KanitBulunamadi(parca_id)
    parca.gorunur_firmaya = gorunur
    return parca


def dosya_anahtarlari(parcalar: list[KanitParcasi]) -> list[str]:
    return [p.dosya_anahtari for p in parcalar if p.dosya_anahtari]


async def depodan_sil(anahtarlar: list[str]) -> None:
    """Commit'ten sonra, arka planda. Hata akışı düşürmez (İ9)."""
    depo = kurulum.depo()
    for anahtar in anahtarlar:
        try:
            await depo.sil(anahtar)
        except Exception:
            logger.warning("depodan silinemedi anahtar=%s", anahtar, exc_info=True)
