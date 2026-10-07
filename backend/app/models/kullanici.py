from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.hesap import Hesap
    from app.models.yetenek_karti import YetenekKarti


class Kullanici(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "kullanici"

    # Profilin sahibi olan hesap (1-1). Nullable: kimlik tablosundan önceki
    # profillerin hesabı yok ve onlar için hesap uydurulmuyor; hesapsız profilin kartı
    # eşleştirmeye girmez (docs/kimlik-ve-dongu.md § 8).
    hesap_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hesap.id", ondelete="CASCADE"), unique=True
    )
    ad: Mapped[str] = mapped_column(String)
    # İletişim bilgisi (kimlik değil: kimlik `hesap`ta). Kayıtta hesap
    # e-postasıyla doldurulur; kuruma yalnızca eşleşme kabul edilince görünür
    # (docs/kimlik-ve-dongu.md § 5). Tekil ve normalize.
    email: Mapped[str] = mapped_column(String, unique=True)
    sehir: Mapped[str | None] = mapped_column(String)
    # Kabul ettiği çalışma modelleri (is_yerinde | hibrit | uzaktan).
    # Şehirden ayrı: "İstanbul'da ama hibrit de olur" ifade edilebilsin.
    # Müsaitlikle karıştırma — o çalışma tipi (tam/yarı zamanlı), bu yeri.
    calisma_modelleri: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default=text("'{}'")
    )
    # Kabul ettiği çalışma tipleri, çoklu (app/core/musaitlik.py kodları:
    # tam_zamanli | yarim_zamanli | proje_bazli | staj). Boş liste "belirtilmedi":
    # eşleştirmede elenmez (docs/kararlar.md G2).
    musaitlikler: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default=text("'{}'")
    )
    # Kayıt formunun yapısal alanları (docs/data-schema.md). Eşleştirme
    # bunlara bakmaz: yalnızca yetkinliğe dayanıyor. Fotoğraf, yaş, cinsiyet gibi
    # alanlar bilinçli olarak YOK. Bu alanlardan önce açılmış profillerde NULL.
    # ogrenci | mezun | calisiyor
    kariyer_durumu: Mapped[str | None] = mapped_column(String)
    okul: Mapped[str | None] = mapped_column(String)
    bolum: Mapped[str | None] = mapped_column(String)
    sinif: Mapped[int | None] = mapped_column(SmallInteger)
    mezuniyet_yili: Mapped[int | None] = mapped_column(SmallInteger)
    musaitlik_baslangici: Mapped[date | None] = mapped_column(Date)
    github_url: Mapped[str | None] = mapped_column(String)
    linkedin_url: Mapped[str | None] = mapped_column(String)
    portfolyo_url: Mapped[str | None] = mapped_column(String)

    hesap: Mapped[Hesap | None] = relationship(back_populates="kullanici")
    # Gencin tek kartı; henüz Keşif'i tamamlamadıysa None.
    yetenek_karti: Mapped[YetenekKarti | None] = relationship(
        back_populates="kullanici", cascade="all, delete-orphan", uselist=False
    )
