from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.yetenek_karti import YetenekKarti


class Kullanici(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "kullanici"

    ad: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    sehir: Mapped[str | None] = mapped_column(String)
    musaitlik: Mapped[str | None] = mapped_column(String)

    yetenek_kartlari: Mapped[list[YetenekKarti]] = relationship(
        back_populates="kullanici", cascade="all, delete-orphan"
    )
