from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.isbirligi import Isbirligi


class Milestone(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "milestone"

    isbirligi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("isbirligi.id", ondelete="CASCADE"), index=True
    )
    baslik: Mapped[str] = mapped_column(String)
    hedef_tarih: Mapped[date | None] = mapped_column(Date)
    durum: Mapped[str] = mapped_column(String)

    isbirligi: Mapped[Isbirligi] = relationship(back_populates="milestonelar")
