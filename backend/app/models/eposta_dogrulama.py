"""Kayıt e-postası doğrulama bağlantısı (docs/dogrulama.md § 6.3).

Token'ın kendisi saklanmaz, SHA-256 özeti saklanır: veritabanı sızsa da
bağlantı üretilemez. Doğrulama sonrası satır süresi dolana kadar kalır; aynı
bağlantının ikinci açılışı hata değil, "zaten doğrulandı"dır.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class EpostaDogrulama(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "eposta_dogrulama"

    hesap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hesap.id", ondelete="CASCADE"), index=True
    )
    token_ozeti: Mapped[str] = mapped_column(String, unique=True)
    son_gecerlilik: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    olusturma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
