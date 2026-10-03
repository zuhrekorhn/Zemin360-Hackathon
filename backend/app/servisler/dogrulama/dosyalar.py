"""Dosya ve görsel kanıtının orkestrasyonu (plan § 4): sınırlar → yükleme hattı → depo →
tek kapıdan parça → değerlendirme.

Depo ve virüs tarayıcı kurulum noktasından gelir (`core/dis_servisler/kurulum.py`).
Dosyanın depodan silinmesi commit'ten SONRA yapılır (arka planda, çağıranın işi):
işlem geri alınırsa satır durur, dosyası da durmalı. Ters yönde (dosya kondu,
işlem düştü) depoda sahipsiz bir dosya kalabilir; zararsızdır, kimse adresini almaz.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dogrulama.kurallar import OkunanKanit
from app.core.config import get_settings
from app.core.dis_servisler import kurulum
from app.core.dosya_hatti import DosyaReddedildi, dosyayi_hazirla, gorunen_ad
from app.models.kanit_parcasi import KanitParcasi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler.dogrulama.kanit import degerlendir
from app.servisler.dogrulama.parcalar import (
    DOSYA_TURLERI,
    KanitBulunamadi,
    dosya_eklenebilir_mi,
    dosya_parcasi_ekle,
    parca_bul,
)

logger = logging.getLogger("zemin360.dosyalar")


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
    anahtar = f"kanit/{uuid.uuid4().hex}"
    belge = {
        "dosya": {
            "ad": gorunen_ad(ham_ad, hazir.icerik_turu),
            "icerik_turu": hazir.icerik_turu,
            "boyut": len(hazir.veri),
            "tarama": hazir.tarama.value,
        },
        **hazir.on_bilgi,
    }
    dosya_eklenebilir_mi(cikti, hazir.ozet)  # depoya bir şey konmadan
    depo = kurulum.depo()
    await depo.koy(anahtar, hazir.veri, hazir.icerik_turu)
    dosya_parcasi_ekle(
        cikti, tur=hazir.parca_turu, dosya_anahtari=anahtar, dosya_ozeti=hazir.ozet, belge=belge
    )
    try:
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
