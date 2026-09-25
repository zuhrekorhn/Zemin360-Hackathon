from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.hesap import Hesap
    from app.models.yetenek_karti import YetenekKarti


class Kullanici(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "kullanici"

    # Profilin sahibi olan hesap (1-1). Nullable: Faz B öncesi profillerin
    # hesabı yok ve onlar için hesap uydurulmuyor; hesapsız profilin kartı
    # eşleştirmeye girmez (docs/faz-b-kimlik-ve-dongu.md § 8).
    hesap_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hesap.id", ondelete="CASCADE"), unique=True
    )
    ad: Mapped[str] = mapped_column(String)
    # Tekil ve normalize (app/core/metin.py › eposta_normalize). Onay anında
    # kayıt bu alanla upsert ediliyor; Faz B'de hesaba bağlanacak.
    email: Mapped[str] = mapped_column(String, unique=True)
    sehir: Mapped[str | None] = mapped_column(String)
    # Kabul ettiği çalışma modelleri (is_yerinde | hibrit | uzaktan).
    # Şehirden ayrı: "İstanbul'da ama hibrit de olur" ifade edilebilsin.
    # Müsaitlikle karıştırma — o çalışma tipi (tam/yarı zamanlı), bu yeri.
    calisma_modelleri: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default=text("'{}'")
    )
    musaitlik: Mapped[str | None] = mapped_column(String)

    hesap: Mapped[Hesap | None] = relationship(back_populates="kullanici")
    yetenek_kartlari: Mapped[list[YetenekKarti]] = relationship(
        back_populates="kullanici", cascade="all, delete-orphan"
    )
