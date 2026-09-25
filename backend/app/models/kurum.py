from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.hesap import Hesap
    from app.models.ihtiyac_karti import IhtiyacKarti


class Kurum(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "kurum"

    # Profilin sahibi olan hesap (1-1); nullable, gerekçesi Kullanici.hesap_id'de.
    hesap_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hesap.id", ondelete="CASCADE"), unique=True
    )
    ad: Mapped[str] = mapped_column(String)
    sektor: Mapped[str | None] = mapped_column(String)
    sehir: Mapped[str | None] = mapped_column(String)
    # Kurum kaydı bu e-postayla bulunur/oluşturulur (Kullanici.email ile aynı
    # desen). Kart yanıtlarında DIŞARIYA VERİLMEZ — bkz. app/schemas/tanimlama.py
    # Tekil ve normalize; NULL birden fazla olabilir (Postgres UNIQUE'i NULL'ları
    # eşit saymaz).
    iletisim_email: Mapped[str | None] = mapped_column(String, index=True, unique=True)

    hesap: Mapped[Hesap | None] = relationship(back_populates="kurum")
    ihtiyac_kartlari: Mapped[list[IhtiyacKarti]] = relationship(
        back_populates="kurum", cascade="all, delete-orphan"
    )
