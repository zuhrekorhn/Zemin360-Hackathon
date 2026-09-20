from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.somut_cikti import SomutCikti


class GuvenSkoru(UUIDPrimaryKeyMixin, Base):
    """Dört bileşenli güven göstergesi; her bileşen 0-3 (agent-specs.md), tek sayıya indirilmez."""

    __tablename__ = "guven_skoru"
    __table_args__ = (
        CheckConstraint("kanit_orijinalligi BETWEEN 0 AND 3", name="kanit_orijinalligi_aralik"),
        CheckConstraint(
            "sonuc_olculebilirligi BETWEEN 0 AND 3", name="sonuc_olculebilirligi_aralik"
        ),
        CheckConstraint("rol_netligi BETWEEN 0 AND 3", name="rol_netligi_aralik"),
        CheckConstraint("ucuncu_taraf_onayi BETWEEN 0 AND 3", name="ucuncu_taraf_onayi_aralik"),
    )

    # Bir çıktının en fazla bir güven skoru var (ER: ||--o|); zamanla güncellenir
    somut_cikti_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("somut_cikti.id", ondelete="CASCADE"), unique=True
    )
    kanit_orijinalligi: Mapped[int] = mapped_column(Integer)
    sonuc_olculebilirligi: Mapped[int] = mapped_column(Integer)
    rol_netligi: Mapped[int] = mapped_column(Integer)
    ucuncu_taraf_onayi: Mapped[int] = mapped_column(Integer)
    gerekce_metni: Mapped[str | None] = mapped_column(Text)

    somut_cikti: Mapped[SomutCikti] = relationship(back_populates="guven_skoru")
