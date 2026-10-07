"""Ücretli dış servislerin dönemlik kullanım sayacı (docs/dogrulama.md § 14.4: aylık tavan).

Sayaç kalıcıdır: tavan, silinen kanıtlar ya da süreç yeniden başlaması yüzünden
aşılmasın. Artırma tek koşullu sorguyla (`servisler/servis_kullanimi.py`).
"""

from __future__ import annotations

from sqlalchemy import Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ServisKullanimi(Base):
    __tablename__ = "servis_kullanimi"

    # Servis adı (kurulum.servis_kipleri ile aynı: "gorsel_arayici")
    servis: Mapped[str] = mapped_column(String, primary_key=True)
    # "YYYY-MM" (UTC)
    donem: Mapped[str] = mapped_column(String, primary_key=True)
    sayi: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
