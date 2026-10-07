"""Gencin tek yetenek kartı (docs/kararlar.md G17).

Bir gencin tek kartı olur; kural veritabanında (`yetenek_karti.kullanici_id`
tekil). Kartı bulmanın tek yolu burası: Keşif ve `/me` kendi sorgusunu
yazmaz, "genç başına kaç kart" varsayımı dağılmaz.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.yetenek_karti import YetenekKarti


async def gencin_karti(oturum: AsyncSession, kullanici_id: uuid.UUID) -> YetenekKarti | None:
    """Gencin kartı; henüz Keşif'i tamamlamadıysa None."""
    return await oturum.scalar(
        select(YetenekKarti).where(YetenekKarti.kullanici_id == kullanici_id)
    )
