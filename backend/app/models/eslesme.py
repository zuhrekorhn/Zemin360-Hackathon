from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.canlilik_olayi import CanlilikOlayi
    from app.models.ihtiyac_karti import IhtiyacKarti
    from app.models.isbirligi import Isbirligi
    from app.models.yetenek_karti import YetenekKarti


class Eslesme(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "eslesme"

    yetenek_karti_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("yetenek_karti.id", ondelete="CASCADE"), index=True
    )
    ihtiyac_karti_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ihtiyac_karti.id", ondelete="CASCADE"), index=True
    )
    skor: Mapped[float] = mapped_column(Float)
    gerekce_metni: Mapped[str | None] = mapped_column(Text)
    # State machine (değer kümesi Faz 2'de Eşleştirme Ajanı ile netleşecek)
    durum: Mapped[str] = mapped_column(String)
    # Canlılık Ajanı bu alanı tarar (agent-specs.md)
    son_aktivite_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    yetenek_karti: Mapped[YetenekKarti] = relationship(back_populates="eslesmeler")
    ihtiyac_karti: Mapped[IhtiyacKarti] = relationship(back_populates="eslesmeler")
    # ER: ESLESME ||--o| ISBIRLIGI (0 veya 1)
    isbirligi: Mapped[Isbirligi | None] = relationship(
        back_populates="eslesme", uselist=False, cascade="all, delete-orphan"
    )
    canlilik_olaylari: Mapped[list[CanlilikOlayi]] = relationship(
        back_populates="eslesme", cascade="all, delete-orphan"
    )
