from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.yetenek_karti import YetenekKarti


class Kullanici(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "kullanici"

    ad: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    sehir: Mapped[str | None] = mapped_column(String)
    # Kabul ettiği çalışma modelleri (is_yerinde | hibrit | uzaktan).
    # Şehirden ayrı: "İstanbul'da ama hibrit de olur" ifade edilebilsin.
    # Müsaitlikle karıştırma — o çalışma tipi (tam/yarı zamanlı), bu yeri.
    calisma_modelleri: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default=text("'{}'")
    )
    musaitlik: Mapped[str | None] = mapped_column(String)

    yetenek_kartlari: Mapped[list[YetenekKarti]] = relationship(
        back_populates="kullanici", cascade="all, delete-orphan"
    )
