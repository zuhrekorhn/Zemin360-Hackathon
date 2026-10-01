"""Gencin bağladığı platform hesabı ve bekleyen doğrulama kodu (plan § 6.1, § 6.2, § 13).

Bağlı hesaptaki çalışma seviye B'dir (`agents/dogrulama/hesap_sahipligi.py`).
Bir platform hesabı iki gence bağlanamaz: (`saglayici`, `dis_kimlik`) tekil.
OAuth token'ı saklanmaz; bağlama anında kimlik okunur, token atılır.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.agents.dogrulama.hesap_sahipligi import YONTEM_ELLE, YONTEM_OAUTH, YONTEM_PROFIL_KODU
from app.core.kanit_okuma.hesap_izi import Saglayici
from app.db.base import Base, UUIDPrimaryKeyMixin

YONTEMLER = (YONTEM_OAUTH, YONTEM_PROFIL_KODU, YONTEM_ELLE)


def _liste(degerler) -> str:
    return ", ".join(f"'{d}'" for d in degerler)


class BagliHesap(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bagli_hesap"
    __table_args__ = (
        UniqueConstraint("saglayici", "dis_kimlik", name="uq_bagli_hesap_dis_kimlik"),
        CheckConstraint(f"saglayici IN ({_liste(Saglayici)})", name="saglayici_gecerli"),
        CheckConstraint(f"yontem IN ({_liste(YONTEMLER)})", name="yontem_gecerli"),
    )

    kullanici_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kullanici.id", ondelete="CASCADE"), index=True
    )
    saglayici: Mapped[str] = mapped_column(String)
    # Görünen ad (GitHub login, YouTube @kanal, kişisel sitenin alan adı).
    kullanici_adi: Mapped[str] = mapped_column(String)
    # Platformun değişmeyen kimliği (GitHub kullanıcı no, ORCID iD…); profil
    # kodunda küçük harfli kullanıcı adı ya da alan adı.
    dis_kimlik: Mapped[str] = mapped_column(String)
    yontem: Mapped[str] = mapped_column(String)
    baglanma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ProfilKodu(UUIDPrimaryKeyMixin, Base):
    """Profil açıklamasına yazılacak kod (`z360-` + 8 karakter, 48 saat).

    Kullanıcı ve platform başına tek kod: yenisi eskisinin yerine geçer.
    Doğrulanınca satır silinir; bağlantı `bagli_hesap`'ta kalıcıdır.
    """

    __tablename__ = "profil_kodu"
    __table_args__ = (
        UniqueConstraint("kullanici_id", "platform", name="uq_profil_kodu_platform"),
        CheckConstraint(f"platform IN ({_liste(Saglayici)})", name="platform_gecerli"),
    )

    kullanici_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kullanici.id", ondelete="CASCADE")
    )
    platform: Mapped[str] = mapped_column(String)
    kod: Mapped[str] = mapped_column(String)
    profil_adresi: Mapped[str] = mapped_column(String)
    son_gecerlilik: Mapped[datetime] = mapped_column(DateTime(timezone=True))
