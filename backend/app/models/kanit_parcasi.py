"""Bir iş kalemine eklenmiş kanıt parçası: link, dosya ya da görsel (plan § 13).

Bir kalemin birden çok parçası olabilir; güven göstergesinde her başlık için
en güçlü parça kullanılır, parçalar toplanmaz (plan § 2). Parçanın okunuşu
(erişim, seviye, platform, okunan metin) burada saklanır; itiraz ve yeniden
değerlendirme sayfayı yeniden okumaz.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import EMBEDDING_DIM, Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.somut_cikti import SomutCikti


class KanitParcasi(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "kanit_parcasi"
    __table_args__ = (
        # Aynı link bir kalemde iki kez olmaz (normal_url: app/core/kanit_okuma/adres.py).
        Index(
            "uq_kanit_parcasi_kalem_normal_url",
            "somut_cikti_id",
            "normal_url",
            unique=True,
            postgresql_where=text("normal_url IS NOT NULL"),
        ),
    )

    somut_cikti_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("somut_cikti.id", ondelete="CASCADE"), index=True
    )
    # ParcaTuru: link | dosya | gorsel
    tur: Mapped[str] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)
    # Kimlik için tek biçim; başka hesapta aynı kanıtı bulmak için de indeksli.
    normal_url: Mapped[str | None] = mapped_column(String, index=True)
    # Dosya / görsel (adım 9): depodaki anahtar, içerik özeti, algısal özet
    dosya_anahtari: Mapped[str | None] = mapped_column(String)
    dosya_ozeti: Mapped[str | None] = mapped_column(String, index=True)
    phash: Mapped[str | None] = mapped_column(String)
    # Okunuş: platform ("github", "youtube"…), ErisimDurumu, KaynakSeviyesi, SahiplikKaynagi
    platform: Mapped[str | None] = mapped_column(String)
    erisim: Mapped[str | None] = mapped_column(String)
    seviye: Mapped[str | None] = mapped_column(String)
    sahiplik_kaynagi: Mapped[str | None] = mapped_column(String)
    # Yazarlar, çapalar, alıntılar, platform verisi
    belge: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # Kişisel veriler maskelenmiş okunan metin; görselde görülen metin
    tam_metin: Mapped[str | None] = mapped_column(Text)
    gorsel_metni: Mapped[str | None] = mapped_column(Text)
    okuma_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Link çürümesi: üst üste "silinmiş ya da gizlenmiş" yoklama sayısı (plan § 10.4)
    curume_sayaci: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    gorunur_firmaya: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    # Kalem işaretleri (ör. "alakasiz_kanit"); kötüye kullanım işaretleri ayrı tabloda.
    isaretler: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default=text("'{}'")
    )
    olusturma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    somut_cikti: Mapped[SomutCikti] = relationship(back_populates="kanit_parcalari")

    @property
    def dosya_adi(self) -> str | None:
        return (self.belge or {}).get("dosya", {}).get("ad")

    @property
    def dosya_boyutu(self) -> int | None:
        return (self.belge or {}).get("dosya", {}).get("boyut")

    @property
    def girvak_incelemesi(self) -> str | None:
        """e-Devlet belgesi: "bekliyor" | "onaylandi" | "reddedildi"; yoksa None."""
        for capa in (self.belge or {}).get("capalar", []):
            if capa.get("tur") == "edevlet":
                return capa.get("girvak_karari") or "bekliyor"
        return None

    metin_parcalari: Mapped[list[KanitMetinParcasi]] = relationship(
        back_populates="kanit_parcasi",
        cascade="all, delete-orphan",
        order_by="KanitMetinParcasi.sira",
    )


class KanitMetinParcasi(UUIDPrimaryKeyMixin, Base):
    """Uzun kanıt metninin embedding'li parçası (plan § 5.4); bir kez hesaplanır."""

    __tablename__ = "kanit_metin_parcasi"
    __table_args__ = (UniqueConstraint("kanit_parcasi_id", "sira"),)

    kanit_parcasi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kanit_parcasi.id", ondelete="CASCADE"), index=True
    )
    sira: Mapped[int] = mapped_column(Integer)
    metin: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))

    kanit_parcasi: Mapped[KanitParcasi] = relationship(back_populates="metin_parcalari")
