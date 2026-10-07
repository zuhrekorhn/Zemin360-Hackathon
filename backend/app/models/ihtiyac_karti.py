from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import EMBEDDING_DIM, Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.eslesme import Eslesme
    from app.models.kurum import Kurum


class IhtiyacKarti(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ihtiyac_karti"

    kurum_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kurum.id", ondelete="CASCADE"), index=True
    )
    problem_tanimi: Mapped[str] = mapped_column(Text)
    basari_kriteri: Mapped[str | None] = mapped_column(Text)
    # Başarı kriterinin parçaları: metrik, mevcut_deger, hedef_deger, sure,
    # olcum_bilinmiyor (app/core/basari_olcutu.py). Bu alandan önceki kartta NULL.
    basari_olcutu: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    kisitlar: Mapped[str | None] = mapped_column(Text)
    # Nullable: Eşleştirme'nin sert filtresi SQL'den çalışsın diye ayrı alanlar (data-schema.md)
    sehir_tercihi: Mapped[str | None] = mapped_column(String)
    # Tek seçim: iş nerede yapılacak (is_yerinde | hibrit | uzaktan).
    calisma_modeli: Mapped[str | None] = mapped_column(String)
    musaitlik_tercihi: Mapped[str | None] = mapped_column(String)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    # Kartı doğuran Tanımlama sohbeti; tekil (onay tekrarlanabilir olsun diye,
    # bkz. YetenekKarti.oturum_id).
    oturum_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True)
    # Eşleştirme "kurumun en son kartı"nı bundan bulur; UUID kronolojik değil
    # (docs/data-schema.md § Tasarım Kararları)
    olusturma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # acik | kapandi (docs/kararlar.md G4). Kapalı ihtiyaç
    # eşleştirmeye girmez; bekleyen ilgiler "kapandı" olur. Kapanan ilan tekrar
    # açılmaz (docs/kararlar.md F7).
    durum: Mapped[str] = mapped_column(String, default="acik", server_default=text("'acik'"))
    # Kimi arıyor (docs/kararlar.md F4-5): genc | firma.
    # Mevcut ilanlar genç ilanı. Ortak ilanında aranan firma türleri (boş =
    # hepsi) ve iş birliği türü; çalışma modeli ve müsaitlik genç ilanına özel.
    aranan: Mapped[str] = mapped_column(String, default="genc", server_default=text("'genc'"))
    aranan_firma_turleri: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default=text("'{}'")
    )
    isbirligi_turu: Mapped[str | None] = mapped_column(String)
    # Firmanın kapatırken seçtiği neden (app/core/ilan.py); yalnızca GİRVAK görür.
    kapanma_nedeni: Mapped[str | None] = mapped_column(String)
    kapanma_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    kurum: Mapped[Kurum] = relationship(back_populates="ihtiyac_kartlari")
    eslesmeler: Mapped[list[Eslesme]] = relationship(
        back_populates="ihtiyac_karti", cascade="all, delete-orphan"
    )
