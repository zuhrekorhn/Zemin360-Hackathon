from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.somut_cikti import SomutCikti


class ReferansIstegi(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "referans_istegi"
    # Değer kümelerinin CHECK'leri migration'da (e4a9c7b2d5f1); kurallar
    # app/agents/dogrulama/ (ILISKILER, YANITLAR, durum makinesi).
    __table_args__ = (CheckConstraint("puan BETWEEN 1 AND 5", name="puan_araligi"),)

    somut_cikti_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("somut_cikti.id", ondelete="CASCADE"), index=True
    )
    referans_email: Mapped[str] = mapped_column(String)
    # Tek kullanımlık, girişsiz yanıt linki için (POST /dogrulama/referans-yaniti).
    # Yalnızca referansa giden e-postada bulunur; hiçbir API yanıtında dönmez.
    token: Mapped[str] = mapped_column(
        String, unique=True, default=lambda: secrets.token_urlsafe(32)
    )
    # State machine: bekliyor -> yanitlandi | yanit_yok (zaman aşımı, ceza değil
    # nötr durum) | geri_cekildi (genç). "yanitlandi" yanıtın geldiğini söyler,
    # olumlu olduğunu değil.
    durum: Mapped[str] = mapped_column(
        String, default="bekliyor", server_default=text("'bekliyor'")
    )
    yanit_metni: Mapped[str | None] = mapped_column(Text)
    # Eski formun 1-5 puanı (dört soruluk formdan önceki yanıtlar); okunmaya devam eder.
    # Yanıtlar kayıtlı tutuluyor çünkü birden fazla referans yanıtlayınca
    # GUVEN_SKORU.ucuncu_taraf_onayi hepsinden hesaplanıyor — son yanıt öncekini ezemez.
    puan: Mapped[int | None] = mapped_column(Integer)
    # 4 soruluk form (docs/dogrulama.md § 7): ilişki ve üç soru (evet / kismen / hayir /
    # bilmiyorum).
    # Soru kalemde boşsa (ör. pay yazılmamış) sorulmaz, NULL kalır.
    iliski: Mapped[str | None] = mapped_column(String)
    iddia_dogru: Mapped[str | None] = mapped_column(String)
    pay_dogru: Mapped[str | None] = mapped_column(String)
    sonuc_dogru: Mapped[str | None] = mapped_column(String)
    # E-postanın kuyruğa verildiği an (istek açılınca); NULL = sistem e-postasından önce açılmış.
    gonderim_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Tek hatırlatma (3. gün, Canlılık taraması); NULL = gitmedi.
    hatirlatma_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Yanıtın şüphe sinyalleri (`referans_supheli`, docs/dogrulama.md § 9).
    yanit_isareti: Mapped[dict | None] = mapped_column(JSONB)
    # Zaman aşımı (5-7 gün) bu tarihten hesaplanır — ayrı bir zamanlayıcı yok,
    # okuma anında değerlendirilir (app/agents/dogrulama/referans_durumu.py)
    olusturma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Yanıtın geldiği an. İş kalemi sonradan değişirse (SomutCikti.icerik_tarihi)
    # bundan önceki yanıtlar geçmiş olarak kalır, puana girmez. Bu alandan önce
    # yanıtlanmışlarda NULL.
    yanit_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    somut_cikti: Mapped[SomutCikti] = relationship(back_populates="referans_istekleri")
