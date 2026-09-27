"""Canlılık uç noktalarının şemaları (docs/faz-d-canlilik.md § 8)."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class TaramaSonucu(BaseModel):
    """Bir taramanın özeti; panelde "son tarama" olarak gösterilir."""

    tarih: dt.datetime
    # tür → yazılan olay sayısı (toplu öneri bildiriminde her eşleşme ayrı olay)
    olaylar: dict[str, int]
    # gönderilen bildirim sayısı (toplu öneri kurum başına bir)
    bildirim: int
    sure_sn: float
