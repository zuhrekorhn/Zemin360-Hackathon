"""Hesap bağlama şemaları (docs/plans/dogrulama-iyilestirme.md § 6)."""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict, Field


class BagliHesapYaniti(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    saglayici: str
    kullanici_adi: str
    # oauth | profil_kodu | elle (GİRVAK'ın doğruladığı kod)
    yontem: str
    baglanma_tarihi: dt.datetime


class HesaplarimYaniti(BaseModel):
    hesaplar: list[BagliHesapYaniti]
    # Bugün açık olan OAuth sağlayıcıları (ayarı olmayan görünmez).
    oauth_saglayicilari: list[str]


class OAuthBaslatYaniti(BaseModel):
    yetki_adresi: str


class OAuthTamamlaIstegi(BaseModel):
    kod: str = Field(min_length=1, max_length=512)
    durum: str = Field(min_length=1, max_length=2048)
