"""Eşleştirme Ajanı uç noktalarının şemaları (docs/api-contracts.md § Eşleştirme)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.schemas.kesif import YetenekKartiYaniti


class EslestirmeCalistirIstegi(BaseModel):
    kurum_id: uuid.UUID


class OneriYaniti(BaseModel):
    """Kuruma gösterilen tek bir öneri.

    Yetenek kartı burada da iletişim bilgisi taşımaz (agent-specs.md § 1.5) —
    Keşif'in kart şeması aynen kullanılıyor.
    """

    eslesme_id: uuid.UUID
    skor: float
    durum: str
    gerekce_metni: str | None
    yetenek_karti: YetenekKartiYaniti


class OnerilerYaniti(BaseModel):
    ihtiyac_karti_id: uuid.UUID
    oneriler: list[OneriYaniti]
    # Havuz küçükken sonuç azlığı gizlenmez, açıkça söylenir
    # (docs/matching-algorithm.md § 5, cold start).
    az_sonuc_uyarisi: bool
    # Liste boş kaldığında arayüz "neden boş"u söyleyebilsin diye eşik
    # yanıtta dönüyor; istemci tarafında sabit tutulursa ikisi ayrışır.
    skor_esigi: float


class IlgileniyorumIstegi(BaseModel):
    eslesme_id: uuid.UUID


class IlgileniyorumYaniti(BaseModel):
    """Kurum ilgilendiğini söyleyince eşleşme kabul edilir ve iş birliği açılır.

    Ayrı bir onay adımı yok — MVP kararı (bkz. README § Proje Durumu).
    """

    eslesme_id: uuid.UUID
    durum: str
    isbirligi_id: uuid.UUID
    isbirligi_durum: str
