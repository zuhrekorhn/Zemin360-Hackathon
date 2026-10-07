from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import EMBEDDING_DIM, Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.eslesme import Eslesme
    from app.models.kurum import Kurum


class FirmaKarti(UUIDPrimaryKeyMixin, Base):
    """Firmanın yetkinlik kartı (docs/kararlar.md F10).

    Firma başına bir kart. Yetenek kartı genişletilmedi: onun alanları (rol,
    deneyim, çalışmalar, güven göstergesi) gence özel. Paylaşılan kısım eşleşme,
    pipeline, ilgi kuralları ve iş birliği. Kurallar app/core/firma_karti.py.
    """

    __tablename__ = "firma_karti"

    kurum_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kurum.id", ondelete="CASCADE"), unique=True
    )
    # Ürün ya da hizmet: firmanın ne yaptığı (zorunlu).
    ne_yapiyoruz: Mapped[str] = mapped_column(Text)
    # Güçlü olunan alanlar (zorunlu, en az 1).
    yetkinlikler: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default=text("'{}'")
    )
    # Yapılan işler, müşteri türleri.
    onceki_isler: Mapped[str | None] = mapped_column(Text)
    # Ne tür ortak aradığı (serbest metin) ve iş birliği türleri. Eşleşme
    # benzerliğine girmez: kart firmanın ne yaptığını temsil eder.
    aranan_isbirligi: Mapped[str | None] = mapped_column(Text)
    isbirligi_turleri: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default=text("'{}'")
    )
    versiyon: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    # Kart onaylanınca/değişince arka planda hesaplanır; o zamana kadar NULL.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    # Kartı doğuran sohbet. Tekil: aynı sohbet ikinci kez onaylanınca mevcut
    # kart döner. Sohbet dışından gelen kartlarda NULL.
    oturum_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True)
    olusturma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    kurum: Mapped[Kurum] = relationship(back_populates="firma_karti")
    # Ortak ilanlarına aday olarak (docs/kararlar.md F11).
    eslesmeler: Mapped[list[Eslesme]] = relationship(
        back_populates="firma_karti", cascade="all, delete-orphan"
    )
