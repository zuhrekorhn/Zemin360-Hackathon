from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.eslesme import Eslesme
    from app.models.hesap import Hesap

# `tur` değer kümesi (docs/kimlik-ve-dongu.md § 6). Canlılık ve Takip
# bildirimleri de aynı tabloya kendi türleriyle yazılır.
TUR_YENI_ONERI = "yeni_oneri"
TUR_ILGI = "ilgi"
TUR_KABUL = "kabul"
TUR_RED = "red"
TUR_REFERANS_YANITI = "referans_yaniti"
TUR_REFERANS_YANIT_YOK = "referans_yanit_yok"  # gence: referans süresinde yanıtlamadı (nötr)
# Takip (docs/takip.md § 7)
TUR_PLAN_ONERILDI = "plan_onerildi"
TUR_PLAN_DUZENLENDI = "plan_duzenlendi"
TUR_PLAN_ONAYI = "plan_onayi"
TUR_PLAN_ONAYLANDI = "plan_onaylandi"
TUR_ADIM_ISARETLENDI = "adim_isaretlendi"
TUR_ADIM_TAMAMLANDI = "adim_tamamlandi"
TUR_ISBIRLIGI_TAMAMLANDI = "isbirligi_tamamlandi"
TUR_ISBIRLIGI_SONLANDI = "isbirligi_sonlandi"  # karşı tarafa: süreç sonlandı (nötr)
# Gençten ilgi (docs/api-contracts.md)
TUR_GENC_ILGI = "genc_ilgi"  # firmaya: bir genç ilgi gösterdi
TUR_KARSILIKLI_ILGI = "karsilikli_ilgi"  # gence: firma da ilgilendi, iş birliği açıldı
TUR_FIRSAT_KAPANDI = "firsat_kapandi"  # gence: bekleyen fırsat kapandı (nötr)
# İlan düzenleme (docs/kararlar.md D1)
TUR_FIRSAT_GUNCELLENDI = "firsat_guncellendi"  # aday tarafına: ilgilendiği ilan düzenlendi
# Firma akışı (docs/kararlar.md F6)
TUR_FIRMA_DOGRULANDI = "firma_dogrulandi"  # firmaya: GİRVAK doğruladı
# GİRVAK inceleme kuyruğu (docs/dogrulama.md § 9)
TUR_INCELEME_SONUCU = "inceleme_sonucu"  # gence: çalışmasıyla ilgili işaret kapandı
TUR_AD_DEGISIKLIGI_SONUCU = "ad_degisikligi_sonucu"  # gence: ad değişikliği talebi sonuçlandı
TUR_HESAP_BAGLAMA_SONUCU = "hesap_baglama_sonucu"  # gence: GİRVAK doğrulama kodunu inceledi
# Link çürümesi (docs/dogrulama.md § 10.4)
TUR_KANIT_CURUDU = "kanit_curudu"  # gence: kanıt linki art arda açılmadı (nötr)


class Bildirim(UUIDPrimaryKeyMixin, Base):
    """Uygulama içi bildirim. Gerçek e-posta gönderilmez (SMTP yok)."""

    __tablename__ = "bildirim"

    hesap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hesap.id", ondelete="CASCADE"), index=True
    )
    tur: Mapped[str] = mapped_column(String)
    metin: Mapped[str] = mapped_column(Text)
    # Eşleşme silinirse (pipeline eskiyen öneriyi temizler) bildirim kalır,
    # yalnızca bağlantısı düşer.
    eslesme_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eslesme.id", ondelete="SET NULL")
    )
    # Zaman INSERT anında veritabanının gerçek saatinden (`clock_timestamp()`).
    # `now()` işlem başlangıcını döner: aynı işlemde yazılan bildirimler (ör.
    # iki tarafa "plan onaylandı") eşit zamanlı olup "en yeni önce" sırası
    # belirsizleşiyordu. Python saati de çare değil: Windows'ta ~15 ms adımla
    # ilerliyor. server_default elle eklenen satırlar için kalıyor.
    olusturma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.clock_timestamp(), server_default=func.now()
    )
    # NULL = okunmadı. Sayaç bunu sayar.
    okundu_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    hesap: Mapped[Hesap] = relationship()
    eslesme: Mapped[Eslesme | None] = relationship()
