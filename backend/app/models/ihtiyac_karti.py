from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import EMBEDDING_DIM, Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.eslesme import Eslesme
    from app.models.kurum import Kurum


class IhtiyacKarti(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ihtiyac_karti"

    kurum_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kurum.id", ondelete="CASCADE"), index=True
    )
    problem_tanimi: Mapped[str] = mapped_column(Text)
    basari_kriteri: Mapped[str | None] = mapped_column(Text)
    kisitlar: Mapped[str | None] = mapped_column(Text)
    # Nullable: Eşleştirme'nin sert filtresi SQL'den çalışsın diye ayrı alanlar (data-schema.md)
    sehir_tercihi: Mapped[str | None] = mapped_column(String)
    # Tek seçim: iş nerede yapılacak (is_yerinde | hibrit | uzaktan).
    calisma_modeli: Mapped[str | None] = mapped_column(String)
    musaitlik_tercihi: Mapped[str | None] = mapped_column(String)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    # Eşleştirme "kurumun en son kartı"nı bundan bulur; UUID kronolojik değil
    # (docs/data-schema.md § Tasarım Kararları)
    olusturma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    kurum: Mapped[Kurum] = relationship(back_populates="ihtiyac_kartlari")
    eslesmeler: Mapped[list[Eslesme]] = relationship(
        back_populates="ihtiyac_karti", cascade="all, delete-orphan"
    )
