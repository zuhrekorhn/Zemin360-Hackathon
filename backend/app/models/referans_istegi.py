from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.somut_cikti import SomutCikti


class ReferansIstegi(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "referans_istegi"
    __table_args__ = (CheckConstraint("puan BETWEEN 1 AND 5", name="puan_araligi"),)

    somut_cikti_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("somut_cikti.id", ondelete="CASCADE"), index=True
    )
    referans_email: Mapped[str] = mapped_column(String)
    # Tek kullanımlık, girişsiz yanıt linki için (POST /dogrulama/referans-yaniti)
    token: Mapped[str] = mapped_column(
        String, unique=True, default=lambda: secrets.token_urlsafe(32)
    )
    # State machine: bekliyor -> yanitlandi | yanit_yok (zaman aşımı, ceza değil
    # nötr durum). "yanitlandi" yanıtın geldiğini söyler, olumlu olduğunu değil.
    durum: Mapped[str] = mapped_column(
        String, default="bekliyor", server_default=text("'bekliyor'")
    )
    yanit_metni: Mapped[str | None] = mapped_column(Text)
    # Referansın 1-5 puanı. Kayıtlı tutuluyor çünkü birden fazla referans
    # yanıtlayınca GUVEN_SKORU.ucuncu_taraf_onayi hepsinden hesaplanıyor
    # (docs/data-schema.md § Tasarım Kararları) — son yanıt öncekini ezemez.
    puan: Mapped[int | None] = mapped_column(Integer)
    # Zaman aşımı (5-7 gün) bu tarihten hesaplanır — ayrı bir zamanlayıcı yok,
    # okuma anında değerlendirilir (app/agents/dogrulama.py)
    olusturma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    somut_cikti: Mapped[SomutCikti] = relationship(back_populates="referans_istekleri")
