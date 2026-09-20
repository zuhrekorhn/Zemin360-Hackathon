from __future__ import annotations

import secrets
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.somut_cikti import SomutCikti


class ReferansIstegi(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "referans_istegi"

    somut_cikti_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("somut_cikti.id", ondelete="CASCADE"), index=True
    )
    referans_email: Mapped[str] = mapped_column(String)
    # Tek kullanımlık, girişsiz yanıt linki için (POST /dogrulama/referans-yaniti)
    token: Mapped[str] = mapped_column(
        String, unique=True, default=lambda: secrets.token_urlsafe(32)
    )
    # State machine: bekliyor -> onaylandi | yanit_yok (zaman aşımı, ceza değil nötr durum)
    durum: Mapped[str] = mapped_column(
        String, default="bekliyor", server_default=text("'bekliyor'")
    )
    yanit_metni: Mapped[str | None] = mapped_column(Text)

    somut_cikti: Mapped[SomutCikti] = relationship(back_populates="referans_istekleri")
