"""Firma kartı: yazma, düzenleme ve eşleştirmeye hazırlama (docs/plans/firma-akisi.md § 4, § 5).

Kural app/core/firma_karti.py'de; burada veritabanı ve arka plan işi.

Hazırlama, yetenek kartındaki desenin aynısı (app/servisler/kart_hazirlama.py):
kart onaylanınca ya da firmanın ne yaptığını anlatan alanlar değişince
yanıttan sonra embedding hesaplanır. İş başında kartın versiyonu beklenenden
büyükse iş çıkar (daha yeni bir iş sırada). Ortak ilanlarıyla yeniden
eşleştirme firma–firma eşleştirmesiyle birlikte eklenecek (plan § 12, adım 7).

Zamanlayıcı yok (CLAUDE.md). Hata yutulur: firma kartını zaten kaydetti.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.embeddings import EmbeddingHatasi, embedding_uret, firma_temsil_metni
from app.core.firma_karti import EMBEDDING_ALANLARI
from app.db.session import get_sessionmaker
from app.models.firma_karti import FirmaKarti
from app.models.kurum import Kurum

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
    return await embedding_hesapla(oturum, kart)


async def embedding_hesapla(oturum: AsyncSession, kart: FirmaKarti) -> bool:
    """Voyage'a ulaşılamazsa False; kart kaybolmaz, sonraki hazırlama yeniden dener."""
    kurum: Kurum = kart.kurum
    metin = firma_temsil_metni(
        ne_yapiyoruz=kart.ne_yapiyoruz,
        yetkinlikler=kart.yetkinlikler,
        onceki_isler=kart.onceki_isler,
        sektor=kurum.sektor,
    )
    try:
        kart.embedding = await embedding_uret(metin, girdi_turu="document")
    except EmbeddingHatasi:
        logger.warning("Firma kartı embedding'i hesaplanamadı (%s)", kart.id, exc_info=True)
        return False
    await oturum.commit()
    return True
