"""Kartın bir yeteneğinin en güçlü kanıtı (docs/dogrulama.md § 11.1).

Model çıkarımı yalnızca kartta yazılı yeteneklerden, alıntıyla seçer; burada
yetenek başına en güçlü puan tutulur. Eşleştirme bonusunun ileride bu veriye
dayanması bir seçenektir (matching-algorithm.md; karar Eşleştirme incelemesinde).
"""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class YetenekKaniti(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "yetenek_kaniti"
    __table_args__ = (
        UniqueConstraint("kart_id", "yetenek"),
        CheckConstraint("en_guclu_puan BETWEEN 0 AND 3", name="en_guclu_puan_aralik"),
    )

    kart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("yetenek_karti.id", ondelete="CASCADE"), index=True
    )
    yetenek: Mapped[str] = mapped_column(String)
    en_guclu_puan: Mapped[int] = mapped_column(Integer)
    # Parça silinirse kanıt kaydı kalır ama kaynağı boşalır (yeniden değerlendirmede tazelenir).
    kaynak_parca_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kanit_parcasi.id", ondelete="SET NULL")
    )
    # KaynakSeviyesi
    seviye: Mapped[str | None] = mapped_column(String)
