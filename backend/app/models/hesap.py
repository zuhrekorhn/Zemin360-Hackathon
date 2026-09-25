from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.kullanici import Kullanici
    from app.models.kurum import Kurum

# Token'daki `rol` claim'inin değer kümesi (docs/faz-b-kimlik-ve-dongu.md § 1)
ROL_GENC = "genc"
ROL_KURUM = "kurum"
ROL_GIRVAK = "girvak"
ROLLER = (ROL_GENC, ROL_KURUM, ROL_GIRVAK)


class Hesap(UUIDPrimaryKeyMixin, Base):
    """Kimlik: giriş yapan hesap. Profil (kullanici/kurum) ayrı tabloda.

    Neden ayrı tablo (not § 1): giriş tek tabloda tek sorgu, GİRVAK'ın
    profile ihtiyacı yok, bildirim ve yetki tek bir kimliğe bağlanıyor.
    Genç hesabının bir `kullanici` profili, kurum hesabının bir `kurum`
    profili olur (1-1); GİRVAK hesabının profili yok.
    """

    __tablename__ = "hesap"
    __table_args__ = (CheckConstraint("rol IN ('genc', 'kurum', 'girvak')", name="rol_gecerli"),)

    # Normalize edilmiş (app/core/metin.py › eposta_normalize); giriş bununla.
    email: Mapped[str] = mapped_column(String, unique=True)
    # argon2id (app/core/kimlik.py). Düz şifre hiçbir yerde saklanmaz.
    sifre_hash: Mapped[str] = mapped_column(String)
    rol: Mapped[str] = mapped_column(String)
    olusturma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    kullanici: Mapped[Kullanici | None] = relationship(back_populates="hesap", uselist=False)
    kurum: Mapped[Kurum | None] = relationship(back_populates="hesap", uselist=False)
