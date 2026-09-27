"""Takip Ajanı uç noktalarının şemaları (docs/faz-c-takip.md § 7)."""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field

from app.schemas.eslestirme import Ilerleme, Iletisim


class MilestoneYaniti(BaseModel):
    id: uuid.UUID
    sira: int
    baslik: str
    aciklama: str | None
    hedef_tarih: dt.date | None
    # bekliyor | tamamlandi
    durum: str
    genc_isaret: dt.datetime | None
    kurum_isaret: dt.datetime | None
    kanit_linki: str | None
    # Okuma anında hesaplanır (hedef tarih geçti, adım tamamlanmadı); saklanmaz.
    gecikmis: bool


class IsbirligiDetayi(BaseModel):
    """`GET /isbirligi/{id}` — iki tarafa aynı görünüm (GİRVAK'a e-postasız)."""

    id: uuid.UUID
    # plan_bekliyor | aktif | tamamlandi
    durum: str
    baslangic_tarihi: dt.date | None
    tamamlanma_tarihi: dt.datetime | None
    eslesme_id: uuid.UUID
    yetenek_karti_id: uuid.UUID
    ihtiyac_karti_id: uuid.UUID
    genc_adi: str
    kurum_adi: str
    rol_alani: str
    problem_tanimi: str
    basari_kriteri: str | None
    genc_plan_onayi: dt.datetime | None
    kurum_plan_onayi: dt.datetime | None
    plan_onerildi_mi: bool
    milestonelar: list[MilestoneYaniti]
    ilerleme: Ilerleme
    durum_ozeti: str | None
    ozet_tarihi: dt.datetime | None
    iletisim: Iletisim | None


class MilestoneEkleIstegi(BaseModel):
    baslik: str = Field(min_length=1, max_length=200)
    aciklama: str | None = Field(default=None, max_length=1000)
    hedef_tarih: dt.date | None = None


class MilestoneGuncelleIstegi(BaseModel):
    """Taslakta başlık/açıklama/tarih; `aktif`'te yalnızca `kanit_linki`.

    Gönderilmeyen alan değişmez (PATCH).
    """

    baslik: str | None = Field(default=None, min_length=1, max_length=200)
    aciklama: str | None = Field(default=None, max_length=1000)
    hedef_tarih: dt.date | None = None
    kanit_linki: str | None = Field(default=None, max_length=500)
