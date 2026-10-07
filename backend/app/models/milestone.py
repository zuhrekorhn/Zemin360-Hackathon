from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.isbirligi import Isbirligi


class Milestone(UUIDPrimaryKeyMixin, Base):
    """İş birliği planının bir adımı (docs/takip.md § 2-3).

    İki taraf ayrı ayrı "tamamlandı" der; ikisi de derse `durum` tamamlandi.
    Gecikme saklanmaz, okuma anında hesaplanır (hedef_tarih < bugün).
    """

    __tablename__ = "milestone"

    isbirligi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("isbirligi.id", ondelete="CASCADE"), index=True
    )
    baslik: Mapped[str] = mapped_column(String)
    # "Ne olunca tamam sayılır" — ölçülebilir tanım.
    aciklama: Mapped[str | None] = mapped_column(Text)
    # Şablondaki adım anahtarı; elle eklenen adımda None.
    asama: Mapped[str | None] = mapped_column(String)
    # Hazırlık önerisi (ajanın kişiselleştirmesi ya da şablon metni).
    oneri: Mapped[str | None] = mapped_column(Text)
    sira: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    hedef_tarih: Mapped[date | None] = mapped_column(Date)
    # bekliyor | tamamlandi (takip_durumu.py)
    durum: Mapped[str] = mapped_column(String)
    genc_isaret: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    kurum_isaret: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # İsteğe bağlı; Doğrulama Ajanı puanlamaz (kapsam dışı).
    kanit_linki: Mapped[str | None] = mapped_column(String)

    isbirligi: Mapped[Isbirligi] = relationship(back_populates="milestonelar")
