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


class PasifBaglanti(BaseModel):
    """Şu an eşiği aşmış bir kayıt (okuma anında; hiçbir şey yazılmaz)."""

    tur: str
    eslesme_id: str
    isbirligi_id: str | None
    genc_adi: str
    kurum_adi: str
    # hareketsiz gün (adim_gecikti'de: hedeften bu yana gün)
    gun: int
    adim: str | None
    # kime hatırlatılacak: "genc" ve/veya "kurum"
    alicilar: list[str]
    # bu tür için bu kayda giden son hatırlatma (yoksa None)
    son_hatirlatma: dt.datetime | None


class CanlilikOlayiYaniti(BaseModel):
    id: str
    tur: str
    mesaj_metni: str | None
    tetiklenme_tarihi: dt.datetime
    alici_adi: str | None
    alici_rol: str | None
    eslesme_id: str
