from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.canlilik_olayi import CanlilikOlayi
    from app.models.ihtiyac_karti import IhtiyacKarti
    from app.models.isbirligi import Isbirligi
    from app.models.yetenek_karti import YetenekKarti


class Eslesme(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "eslesme"
    # Bir ihtiyaç kartı ile bir yetenek kartı arasında tek eşleşme olur.
    # Arka plan işi ile GET /oneriler aynı anda çalışınca mükerrer satır
    # açılıyordu; pipeline artık bu kısıta ON CONFLICT ile dayanıyor.
    __table_args__ = (UniqueConstraint("ihtiyac_karti_id", "yetenek_karti_id"),)

    yetenek_karti_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("yetenek_karti.id", ondelete="CASCADE"), index=True
    )
    ihtiyac_karti_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ihtiyac_karti.id", ondelete="CASCADE"), index=True
    )
    skor: Mapped[float] = mapped_column(Float)
    gerekce_metni: Mapped[str | None] = mapped_column(Text)
    # State machine: onerildi → ilgileniliyor → kabul_edildi | reddedildi
    # (değer kümesi docs/data-schema.md § Tasarım Kararları'nda;
    #  sabitler app/agents/eslestirme.py içinde DURUM_* olarak)
    durum: Mapped[str] = mapped_column(String)
    # Canlılık Ajanı bu alanı tarar (agent-specs.md)
    son_aktivite_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # İlginin kaydı (docs/plans/genc-akisi.md § 3.5). Karar `durum`'da; bu alanlar
    # yalnızca "kim, ne zaman" bilgisini taşır, hiçbir kural onlara bakmaz.
    # genc | kurum: ilk ilgiyi kim gösterdi (eski kurum ilgileri migration'da "kurum")
    baslatan: Mapped[str | None] = mapped_column(String)
    genc_ilgi_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Gencin "kurum da ilgilenirse e-postam paylaşılsın" onayı
    genc_iletisim_onayi_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    kurum_ilgi_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    yetenek_karti: Mapped[YetenekKarti] = relationship(back_populates="eslesmeler")
    ihtiyac_karti: Mapped[IhtiyacKarti] = relationship(back_populates="eslesmeler")
    # ER: ESLESME ||--o| ISBIRLIGI (0 veya 1)
    isbirligi: Mapped[Isbirligi | None] = relationship(
        back_populates="eslesme", uselist=False, cascade="all, delete-orphan"
    )
    canlilik_olaylari: Mapped[list[CanlilikOlayi]] = relationship(
        back_populates="eslesme", cascade="all, delete-orphan"
    )
