from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, false
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.eslesme import Eslesme
    from app.models.milestone import Milestone


class Isbirligi(UUIDPrimaryKeyMixin, Base):
    """Genç kabul edince açılan iş birliği (docs/faz-c-takip.md § 2).

    `durum`: plan_bekliyor → aktif → tamamlandi. Geçiş kuralları
    app/agents/takip_durumu.py'de; bu model yalnızca sonucu tutar.
    """

    __tablename__ = "isbirligi"

    # Bir eşleşme en fazla bir iş birliğine dönüşür (ER: ||--o|)
    eslesme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eslesme.id", ondelete="CASCADE"), unique=True
    )
    baslangic_tarihi: Mapped[date | None] = mapped_column(Date)
    durum: Mapped[str] = mapped_column(String)

    # Plan onayı: iki taraf da mevcut hâli onaylayınca `aktif`. Plan
    # düzenlenince ikisi de sıfırlanır (herkes son hâli onaylasın).
    genc_plan_onayi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    kurum_plan_onayi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Son milestone iki tarafça tamamlandığı an (kural, ajanın kararı değil).
    tamamlanma_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Takip Ajanı'nın kısa durum özeti (kesilebilir iş; boş kalabilir).
    durum_ozeti: Mapped[str | None] = mapped_column(Text)
    ozet_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Ajan bu iş birliği için plan önerdi mi? Kabuldeki arka plan işi ikinci
    # kez çalışıp tarafların planını ezmesin.
    plan_onerildi_mi: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    eslesme: Mapped[Eslesme] = relationship(back_populates="isbirligi")
    milestonelar: Mapped[list[Milestone]] = relationship(
        back_populates="isbirligi",
        cascade="all, delete-orphan",
        order_by="Milestone.sira",
    )
