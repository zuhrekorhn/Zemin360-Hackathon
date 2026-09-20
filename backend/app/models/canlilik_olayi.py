from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.eslesme import Eslesme


class CanlilikOlayi(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "canlilik_olayi"

    # ISBIRLIGI'na değil ESLESME'ye bağlı: iş birliği başlamadan da pasiflik izlenebilsin
    eslesme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eslesme.id", ondelete="CASCADE"), index=True
    )
    tetiklenme_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    tur: Mapped[str] = mapped_column(String)
    mesaj_metni: Mapped[str | None] = mapped_column(Text)

    eslesme: Mapped[Eslesme] = relationship(back_populates="canlilik_olaylari")
