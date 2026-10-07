"""Firma kartı: yazma, düzenleme ve eşleştirmeye hazırlama (docs/kararlar.md F5, § 5).

Kural app/core/firma_karti.py'de; burada veritabanı ve arka plan işi.

Hazırlama, yetenek kartındaki desenin aynısı (app/servisler/kart_hazirlama.py):
kart onaylanınca ya da firmanın ne yaptığını anlatan alanlar değişince
yanıttan sonra embedding hesaplanır, ardından kartla ilgili açık ortak
ilanları için mevcut pipeline çalışır: sonradan gelen firma da mevcut
ilanlarla eşleşir. İş başında kartın versiyonu beklenenden büyükse iş çıkar
(daha yeni bir iş sırada). Pipeline ilan başına kilitli ve ON CONFLICT'li.

Zamanlayıcı yok (CLAUDE.md). Hata yutulur: firma kartını zaten kaydetti.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.eslestirme import DURUM_ONERILDI, FIRMA_BENZERLIK_ALT_SINIRI
from app.core.firma_karti import EMBEDDING_ALANLARI
from app.core.ilan import ARANAN_FIRMA
from app.db.session import get_sessionmaker
from app.models.eslesme import Eslesme
from app.models.firma_karti import FirmaKarti
from app.models.ihtiyac_karti import IhtiyacKarti
from app.servisler import eslestirme as eslestirme_servisi
from app.servisler.embedding import embedding_hesapla

logger = logging.getLogger("zemin360.firma_karti")

KART_ALANLARI: tuple[str, ...] = (
    "ne_yapiyoruz",
    "yetkinlikler",
    "onceki_isler",
    "aranan_isbirligi",
    "isbirligi_turleri",
)


def kart_alanlarini_yaz(kart: FirmaKarti, degerler: dict[str, Any]) -> set[str]:
    """Gönderilen alanları yazar. Döner: gerçekten değişen alanlar."""
    degisenler: set[str] = set()
    for alan, deger in degerler.items():
        if alan not in KART_ALANLARI:
            continue
        yeni = list(deger) if isinstance(deger, list | tuple) else deger
        if alan in ("yetkinlikler", "isbirligi_turleri") and yeni is None:
            yeni = []
        if getattr(kart, alan) != yeni:
            setattr(kart, alan, yeni)
            degisenler.add(alan)
    return degisenler


def embedding_yenilenmeli_mi(degisenler: set[str]) -> bool:
    return bool(degisenler & EMBEDDING_ALANLARI)


async def kurumun_karti(
    oturum: AsyncSession, kurum_id: uuid.UUID, *, kilitle: bool = False
) -> FirmaKarti | None:
    sorgu = (
        select(FirmaKarti)
        .options(selectinload(FirmaKarti.kurum))
        .where(FirmaKarti.kurum_id == kurum_id)
        .execution_options(populate_existing=True)
    )
    if kilitle:
        sorgu = sorgu.with_for_update(of=FirmaKarti)
    return await oturum.scalar(sorgu)


async def karti_olustur(
    oturum: AsyncSession,
    kurum_id: uuid.UUID,
    degerler: dict[str, Any],
    oturum_id: uuid.UUID | None = None,
) -> FirmaKarti:
    """Yeni kart; commit çağıranın işi. Firmanın kartı zaten varsa çağıran karar verir."""
    kart = FirmaKarti(kurum_id=kurum_id, oturum_id=oturum_id, versiyon=1)
    kart_alanlarini_yaz(kart, degerler)
    oturum.add(kart)
    await oturum.flush()
    return kart


# --- Hazırlama ---------------------------------------------------------------------------


async def firma_kartini_hazirla(kart_id: uuid.UUID, versiyon: int) -> None:
    """Arka plan işi: kendi oturumunu açar, hatayı yutar (bkz. modül notu)."""
    async with get_sessionmaker()() as oturum:
        try:
            await firma_kartini_hazirla_oturumla(oturum, kart_id, versiyon)
        except Exception:
            logger.exception("Firma kartı hazırlama başarısız (%s)", kart_id)


async def firma_kartini_yeniden_eslestir(kart_id: uuid.UUID) -> None:
    """Arka plan işi: embedding aynı, firmanın şehri ya da türü değişti (kesin şartlar).

    Kartın aday olduğu açık ortak ilanları için pipeline yeniden çalışır; kendi
    oturumunu açar, hatayı yutar (profil zaten kaydedildi).
    """
    async with get_sessionmaker()() as oturum:
        try:
            await firma_kartini_eslestir(oturum, kart_id)
        except Exception:
            logger.exception("Firma kartı yeniden eşleştirme başarısız (%s)", kart_id)


async def firma_kartini_hazirla_oturumla(
    oturum: AsyncSession, kart_id: uuid.UUID, versiyon: int
) -> bool:
    """Döner: embedding yazıldı mı."""
    kart = await oturum.scalar(
        select(FirmaKarti)
        .options(selectinload(FirmaKarti.kurum))
        .where(FirmaKarti.id == kart_id)
        .execution_options(populate_existing=True)
    )
    if kart is None or kart.versiyon > versiyon:
        return False
    if not await embedding_hesapla(oturum, kart):
        # Embedding'siz kart eşleşmeye giremez; sonraki hazırlama yeniden dener.
        return False
    await firma_kartini_eslestir(oturum, kart_id)
    return True


async def ilgili_ortak_ilanlari(oturum: AsyncSession, kart_id: uuid.UUID) -> list[uuid.UUID]:
    """Bu kart için pipeline'ı çalıştırılacak ortak ilanları (yetenek kartındaki desen).

    (a) Açık, embedding'i olan, firmanın kendi ilanı olmayan ve kartla benzerliği
        alt sınırı geçen ortak ilanları; (b) kartın hâlâ `onerildi` önerisi olan
        ilanlar (kart artık uymuyorsa öneri temizlensin). Kesin şartlar pipeline'da.
    """
    kartin_firmasi = select(FirmaKarti.kurum_id).where(FirmaKarti.id == kart_id)
    uzaklik = IhtiyacKarti.embedding.cosine_distance(
        select(FirmaKarti.embedding).where(FirmaKarti.id == kart_id).scalar_subquery()
    )
    onerildigi = select(Eslesme.ihtiyac_karti_id).where(
        Eslesme.firma_karti_id == kart_id, Eslesme.durum == DURUM_ONERILDI
    )
    satirlar = await oturum.scalars(
        select(IhtiyacKarti.id).where(
            IhtiyacKarti.embedding.isnot(None),
            IhtiyacKarti.durum == eslestirme_servisi.IHTIYAC_ACIK,
            IhtiyacKarti.aranan == ARANAN_FIRMA,
            IhtiyacKarti.kurum_id != kartin_firmasi.scalar_subquery(),
            or_(uzaklik <= 1.0 - FIRMA_BENZERLIK_ALT_SINIRI, IhtiyacKarti.id.in_(onerildigi)),
        )
    )
    return list(satirlar)


async def firma_kartini_eslestir(oturum: AsyncSession, kart_id: uuid.UUID) -> int:
    """İlgili her ortak ilanı için mevcut pipeline. Döner: kaç ilan."""
    ilan_idleri = await ilgili_ortak_ilanlari(oturum, kart_id)
    for ilan_id in ilan_idleri:
        ilan = await oturum.get(IhtiyacKarti, ilan_id)
        if ilan is None:
            continue
        try:
            await eslestirme_servisi.pipeline_calistir(oturum, ilan)
        except HTTPException as hata:
            logger.info("Eşleştirme atlandı (%s): %s", ilan_id, hata.detail)
    return len(ilan_idleri)


async def onerilerin_gerekcesini_bosalt(oturum: AsyncSession, kart_id: uuid.UUID) -> None:
    """Kart değişince yalnızca `onerildi` önerilerin gerekçesi boşaltılır; pipeline
    yenisini yazar. Karar verilmiş kayıtlara dokunulmaz (genç kartındaki kural)."""
    await oturum.execute(
        update(Eslesme)
        .where(Eslesme.firma_karti_id == kart_id, Eslesme.durum == DURUM_ONERILDI)
        .values(gerekce_metni=None, aday_gerekce_metni=None, uygunluk=None)
    )
