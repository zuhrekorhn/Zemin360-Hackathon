from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ihtiyac_karti import IhtiyacKarti


class Kurum(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "kurum"

    ad: Mapped[str] = mapped_column(String)
    sektor: Mapped[str | None] = mapped_column(String)
    sehir: Mapped[str | None] = mapped_column(String)
    # Kurum kaydı bu e-postayla bulunur/oluşturulur (Kullanici.email ile aynı
    # desen). Kart yanıtlarında DIŞARIYA VERİLMEZ — bkz. app/schemas/tanimlama.py
    iletisim_email: Mapped[str | None] = mapped_column(String, index=True)

    ihtiyac_kartlari: Mapped[list[IhtiyacKarti]] = relationship(
        back_populates="kurum", cascade="all, delete-orphan"
    )
