from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.eslesme import Eslesme
    from app.models.hesap import Hesap

# `tur` değer kümesi (docs/faz-b-kimlik-ve-dongu.md § 6). Canlılık ve Takip
# bildirimleri Faz C/D'de aynı tabloya kendi türleriyle yazılacak.
TUR_YENI_ONERI = "yeni_oneri"
TUR_ILGI = "ilgi"
TUR_KABUL = "kabul"
TUR_RED = "red"
TUR_REFERANS_YANITI = "referans_yaniti"


class Bildirim(UUIDPrimaryKeyMixin, Base):
    """Uygulama içi bildirim. Gerçek e-posta gönderilmez (SMTP yok)."""

    __tablename__ = "bildirim"

    hesap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hesap.id", ondelete="CASCADE"), index=True
    )
    tur: Mapped[str] = mapped_column(String)
    metin: Mapped[str] = mapped_column(Text)
    # Eşleşme silinirse (pipeline eskiyen öneriyi temizler) bildirim kalır,
    # yalnızca bağlantısı düşer.
    eslesme_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eslesme.id", ondelete="SET NULL")
    )
    olusturma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # NULL = okunmadı. Sayaç bunu sayar.
    okundu_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    hesap: Mapped[Hesap] = relationship()
    eslesme: Mapped[Eslesme | None] = relationship()
