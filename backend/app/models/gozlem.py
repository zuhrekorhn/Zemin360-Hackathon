"""Doğrulamanın kalıcı gözlem kayıtları (plan § 10.3, § 14.4).

Üç tablo, hiçbiri kişi ya da adres taşımaz: yalnızca "ne oldu, ne kadar sürdü".
  - `kanit_gozlemi`: bir kanıt parçasının her okunuşu (platform, okuyucu, erişim, seviye);
    GİRVAK panelinde platform bazında erişim dağılımı buradan çıkar.
  - `degerlendirme_gozlemi`: modelin çağrıldığı her değerlendirme (süre, token).
  - `servis_gunlugu`: dış servis başına günlük başarı / hata sayısı; sağlık kaydı
    süreç yeniden başlayınca sıfırlanmasın diye.
Kayıtlar 90 gün sonra Canlılık taramasında silinir.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, DateTime, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin

SAKLAMA_GUN = 90

# KanitGozlemi.kaynak
KAYNAK_DEGERLENDIRME = "degerlendirme"
KAYNAK_YOKLAMA = "yoklama"


class KanitGozlemi(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "kanit_gozlemi"
    __table_args__ = (Index("ix_kanit_gozlemi_tarih", "tarih"),)

    tarih: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # "degerlendirme" | "yoklama" (link çürümesi)
    kaynak: Mapped[str] = mapped_column(String)
    platform: Mapped[str] = mapped_column(String)
    # Linki kimin okuduğu: "dogrudan" | "yedek" (tarayıcı) | "uzak" (Jina)
    okuyucu: Mapped[str] = mapped_column(String)
    erisim: Mapped[str] = mapped_column(String)
    seviye: Mapped[str | None] = mapped_column(String)
    sure_ms: Mapped[int | None] = mapped_column(Integer)
    # Değerlendirmenin girdi özeti (aynı özet = aynı girdi); yoklamada boş.
    girdi_ozeti: Mapped[str | None] = mapped_column(String)


class DegerlendirmeGozlemi(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "degerlendirme_gozlemi"
    __table_args__ = (Index("ix_degerlendirme_gozlemi_tarih", "tarih"),)

    tarih: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    girdi_ozeti: Mapped[str | None] = mapped_column(String)
    parca_sayisi: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    sure_ms: Mapped[int] = mapped_column(Integer)
    model_cagrisi: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    girdi_token: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    cikti_token: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))


class ServisGunlugu(Base):
    __tablename__ = "servis_gunlugu"

    servis: Mapped[str] = mapped_column(String, primary_key=True)
    gun: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    basari_sayisi: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    hata_sayisi: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    son_basari: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    son_hata: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    # Hata sınıfının adı; mesaj değil (mesajda adres ya da anahtar olabilir).
    son_hata_turu: Mapped[str | None] = mapped_column(String)
