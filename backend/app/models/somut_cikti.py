from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.guven_skoru import GuvenSkoru
    from app.models.referans_istegi import ReferansIstegi
    from app.models.yetenek_karti import YetenekKarti


class SomutCikti(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "somut_cikti"

    yetenek_karti_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("yetenek_karti.id", ondelete="CASCADE"), index=True
    )
    baslik: Mapped[str] = mapped_column(String)
    aciklama: Mapped[str | None] = mapped_column(Text)
    # Kanıt henüz eklenmemiş olabilir (kanit_bekleyen akışı)
    kanit_linki: Mapped[str | None] = mapped_column(String)
    kanit_turu: Mapped[str | None] = mapped_column(String)
    tarih: Mapped[date | None] = mapped_column(Date)

    yetenek_karti: Mapped[YetenekKarti] = relationship(back_populates="somut_ciktilar")
    # ER: SOMUT_CIKTI ||--o| GUVEN_SKORU (0 veya 1)
    guven_skoru: Mapped[GuvenSkoru | None] = relationship(
        back_populates="somut_cikti", uselist=False, cascade="all, delete-orphan"
    )
    referans_istekleri: Mapped[list[ReferansIstegi]] = relationship(
        back_populates="somut_cikti", cascade="all, delete-orphan"
    )
