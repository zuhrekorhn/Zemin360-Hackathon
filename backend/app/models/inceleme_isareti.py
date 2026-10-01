"""GİRVAK inceleme kuyruğundaki işaret (docs/plans/dogrulama-iyilestirme.md § 9).

İşaret puanı kendiliğinden değiştirmez (İ1): ajan sinyal toplar, karar
GİRVAK'ındır. Durum geçişleri `app/agents/inceleme_durumu.py`'de, kararın türe
özel etkisi `app/servisler/inceleme_isleyicileri.py`'de.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.agents.inceleme_durumu import ACIK, DURUMLAR
from app.db.base import Base, UUIDPrimaryKeyMixin

# Plan § 9'daki türlerin hepsi baştan tanımlı: sonraki adımlar işaret açmak
# için şema değiştirmez. `alakasiz_kanit` kalem işaretidir, kuyruğa girmez.
TUR_AYNI_IDDIA_COK_HESAPTA = "ayni_iddia_cok_hesapta"
TUR_AYNI_BELGE_IKI_HESAPTA = "ayni_belge_iki_hesapta"
TUR_GORSEL_BASKASINDA = "gorsel_baskasinda"
TUR_REFERANS_SUPHELI = "referans_supheli"
TUR_BELGE_TUTARSIZ = "belge_tutarsiz"
TUR_KANIT_CELISIYOR = "kanit_celisiyor"
TUR_ITIRAZ_SINIRI = "itiraz_siniri"
TUR_AD_DEGISIKLIGI = "ad_degisikligi"
TUR_PROFIL_KODU_ELLE = "profil_kodu_elle"
TUR_EPOSTA_BARKODU = "eposta_barkodu"
TURLER = (
    TUR_AYNI_IDDIA_COK_HESAPTA,
    TUR_AYNI_BELGE_IKI_HESAPTA,
    TUR_GORSEL_BASKASINDA,
    TUR_REFERANS_SUPHELI,
    TUR_BELGE_TUTARSIZ,
    TUR_KANIT_CELISIYOR,
    TUR_ITIRAZ_SINIRI,
    TUR_AD_DEGISIKLIGI,
    TUR_PROFIL_KODU_ELLE,
    TUR_EPOSTA_BARKODU,
)


def _liste(degerler: tuple[str, ...]) -> str:
    return ", ".join(f"'{d}'" for d in degerler)


class IncelemeIsareti(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "inceleme_isareti"
    __table_args__ = (
        CheckConstraint(f"tur IN ({_liste(TURLER)})", name="tur_gecerli"),
        CheckConstraint(f"durum IN ({_liste(DURUMLAR)})", name="durum_gecerli"),
        # Aynı konu için tek açık işaret: tekrar eden sinyal yeni satır değil,
        # açık işaretin ayrıntısına eklenir (servis: isaret_ac).
        Index(
            "uq_inceleme_isareti_acik",
            "tur",
            "kullanici_id",
            "somut_cikti_id",
            unique=True,
            postgresql_where=text("durum = 'acik'"),
            postgresql_nulls_not_distinct=True,
        ),
    )

    tur: Mapped[str] = mapped_column(String)
    kullanici_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kullanici.id", ondelete="CASCADE"), index=True
    )
    # Kalemle ilgili işaretlerde dolu (itiraz sınırı, kanıt işaretleri); ad değişikliğinde boş.
    somut_cikti_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("somut_cikti.id", ondelete="CASCADE")
    )
    # Türe özel bağlam (ör. eski ve istenen ad, itiraz notları). E-posta yazılmaz.
    ayrinti: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    durum: Mapped[str] = mapped_column(String, default=ACIK, server_default=ACIK)
    girvak_notu: Mapped[str | None] = mapped_column(Text)
    olusturma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    kapanma_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
