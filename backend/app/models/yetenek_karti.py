from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import EMBEDDING_DIM, Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.eslesme import Eslesme
    from app.models.kullanici import Kullanici
    from app.models.somut_cikti import SomutCikti


class YetenekKarti(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "yetenek_karti"

    # Gencin tek kartı (docs/kararlar.md G17): kart genç büyüdükçe düzenlenir ve
    # çalışma eklenerek güçlenir, yenisi açılmaz. Kural veritabanında ki
    # eşzamanlı iki onay da ikinci kartı açamasın; tekillik indeksi aramaları
    # da karşılıyor, ayrı indeks gerekmiyor.
    kullanici_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kullanici.id", ondelete="CASCADE"), unique=True
    )
    rol_alani: Mapped[str] = mapped_column(String)
    deneyim_seviyesi: Mapped[str] = mapped_column(String)
    sektor_ilgi_alani: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default=text("'{}'")
    )
    araclar_teknolojiler: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default=text("'{}'")
    )
    # Opsiyonel; Keşif sohbetinde ya da kart düzenlemede eklenir.
    sertifikalar: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default=text("'{}'")
    )
    diller: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default=text("'{}'")
    )
    kanit_bekleyen: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    versiyon: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    # Kart onaylanınca/güncellenince hesaplanır; o zamana kadar NULL
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    # Kartı doğuran Keşif sohbeti. Tekil: aynı sohbet ikinci kez onaylanınca
    # yeni kart açılmaz, bu kart döner (çift tıklama, embedding hatası sonrası
    # yeniden deneme). Sohbet dışından gelen kartlarda NULL.
    oturum_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True)
    # Canlılık'ın "eski kart" kuralı (yeni fırsat) bu tarihe bakar
    # (docs/canlilik.md § 2).
    olusturma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    kullanici: Mapped[Kullanici] = relationship(back_populates="yetenek_karti")
    somut_ciktilar: Mapped[list[SomutCikti]] = relationship(
        back_populates="yetenek_karti", cascade="all, delete-orphan"
    )
    eslesmeler: Mapped[list[Eslesme]] = relationship(
        back_populates="yetenek_karti", cascade="all, delete-orphan"
    )
