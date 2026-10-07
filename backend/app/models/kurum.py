from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.firma_karti import FirmaKarti
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
    # İletişim bilgisi (kimlik `hesap`ta). Kayıtta hesap e-postasıyla
    # doldurulur; gence yalnızca eşleşme kabul edilince görünür. Tekil ve
    # normalize; NULL birden fazla olabilir (UNIQUE NULL'ları eşit saymaz).
    iletisim_email: Mapped[str | None] = mapped_column(String, index=True, unique=True)

    # Kayıt formu (docs/kararlar.md F2). Kural ve değer kümeleri
    # app/core/firma_profili.py'de. Eski hesaplarda boş olabilir (bant).
    # girisim | kobi | kurumsal
    tur: Mapped[str | None] = mapped_column(String)
    web_sitesi: Mapped[str | None] = mapped_column(String)
    # 1-10 | 11-50 | 51-250 | 250+
    calisan_araligi: Mapped[str | None] = mapped_column(String)
    kurulus_yili: Mapped[int | None] = mapped_column(Integer)
    tanitim: Mapped[str | None] = mapped_column(Text)
    # Formu dolduran kişi (firmanın temsilcisi); iletişim bilgisi değil.
    yetkili_ad: Mapped[str | None] = mapped_column(String)
    yetkili_gorev: Mapped[str | None] = mapped_column(String)

    # Firma doğrulaması (docs/kararlar.md F6): bekliyor | dogrulandi |
    # simdilik_degil. Karar GİRVAK'ın; alan adı ipucu saklanmaz
    # (app/core/firma_dogrulama.py). Web sitesi değişince `bekliyor`a döner.
    dogrulama_durumu: Mapped[str] = mapped_column(
        String, default="bekliyor", server_default=text("'bekliyor'")
    )
    dogrulama_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    hesap: Mapped[Hesap | None] = relationship(back_populates="kurum")
    # Firma kartı (firma başına bir tane, isteğe bağlı; docs/kararlar.md F9).
    firma_karti: Mapped[FirmaKarti | None] = relationship(
        back_populates="kurum", uselist=False, cascade="all, delete-orphan"
    )
    ihtiyac_kartlari: Mapped[list[IhtiyacKarti]] = relationship(
        back_populates="kurum", cascade="all, delete-orphan"
    )
