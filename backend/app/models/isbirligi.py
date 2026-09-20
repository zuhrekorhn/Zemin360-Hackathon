from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.eslesme import Eslesme
    from app.models.milestone import Milestone


class Isbirligi(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "isbirligi"

    # Bir eşleşme en fazla bir iş birliğine dönüşür (ER: ||--o|)
    eslesme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eslesme.id", ondelete="CASCADE"), unique=True
    )
    baslangic_tarihi: Mapped[date | None] = mapped_column(Date)
    durum: Mapped[str] = mapped_column(String)

    eslesme: Mapped[Eslesme] = relationship(back_populates="isbirligi")
    milestonelar: Mapped[list[Milestone]] = relationship(
        back_populates="isbirligi", cascade="all, delete-orphan"
    )
