from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.eslesme import Eslesme


class CanlilikOlayi(UUIDPrimaryKeyMixin, Base):
    """Canlılık Ajanı'nın bir hatırlatması ya da fırsat bildirimi (docs/canlilik.md).

    Tekrar kuralı (§ 3) bu tablodan okunur: aynı anahtar için kaydın son
    hareketinden SONRA yazılmış bir olay varsa yenisi yazılmaz.
    """

    __tablename__ = "canlilik_olayi"
    # Tekrar kuralının sorgusu: (eşleşme, tür) için en son olay.
    __table_args__ = (Index("ix_canlilik_olayi_anahtar", "eslesme_id", "tur", "tetiklenme_tarihi"),)

    # ISBIRLIGI'na değil ESLESME'ye bağlı: iş birliği başlamadan da pasiflik izlenebilsin
    eslesme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eslesme.id", ondelete="CASCADE"), index=True
    )
    # INSERT anında gerçek saat (bildirimdeki gibi): aynı taramada yazılan
    # olayların sırası kararlı kalsın.
    tetiklenme_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.clock_timestamp(), server_default=func.now()
    )
    # oneri_bekliyor | ilgi_yanitsiz_1 | ilgi_yanitsiz_2 | plan_onaysiz |
    # isbirligi_hareketsiz | adim_gecikti | yeni_firsat (canlilik_kurallari.py)
    tur: Mapped[str] = mapped_column(String)
    mesaj_metni: Mapped[str | None] = mapped_column(Text)
    # Kime gitti; tekrar anahtarının parçası (aynı kayıtta iki alıcı olabilir).
    alici_hesap_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hesap.id", ondelete="SET NULL")
    )
    # adim_gecikti: adım başına tekrar anahtarı.
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("milestone.id", ondelete="SET NULL")
    )
    # yeni_firsat ve toplu oneri_bekliyor: hangi ihtiyaç kartı.
    ihtiyac_karti_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ihtiyac_karti.id", ondelete="SET NULL")
    )

    eslesme: Mapped[Eslesme] = relationship(back_populates="canlilik_olaylari")
