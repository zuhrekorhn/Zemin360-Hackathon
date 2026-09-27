"""Bildirim uç noktalarının şemaları (docs/faz-b-kimlik-ve-dongu.md § 6)."""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel


class BildirimYaniti(BaseModel):
    id: uuid.UUID
    # yeni_oneri | ilgi | kabul | red | referans_yaniti — arayüz bağlantıyı
    # buna göre seçer (kurum önerilere, genç paneline gider).
    tur: str
    metin: str
    eslesme_id: uuid.UUID | None
    # Eşleşmenin iş birliği varsa (Faz C): arayüz bildirimi doğrudan iş
    # birliği sayfasına bağlar.
    isbirligi_id: uuid.UUID | None = None
    olusturma_tarihi: dt.datetime
    okundu_tarihi: dt.datetime | None

    model_config = {"from_attributes": True}


class HepsiniOkuYaniti(BaseModel):
    okunan: int
