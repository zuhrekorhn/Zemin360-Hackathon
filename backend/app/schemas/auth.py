"""Kayıt, giriş ve /me şemaları (docs/faz-b-kimlik-ve-dongu.md § 1-2)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.core.kimlik import SIFRE_EN_AZ
from app.schemas.sohbet import DoluMetin


class KayitIstegi(BaseModel):
    email: EmailStr
    # Üst sınır: argon2 uzun girdiyi işler ama sınırsız gövde bir DoS kapısı.
    sifre: str = Field(min_length=SIFRE_EN_AZ, max_length=256)
    # GİRVAK açık kayıtla açılamaz (not § 2): yalnızca betik/tohum veriyle.
    rol: Literal["genc", "kurum"]
    # Gencin adı ya da kurumun adı; profil bununla açılır.
    ad: DoluMetin


class GirisIstegi(BaseModel):
    email: EmailStr
    sifre: str = Field(min_length=1, max_length=256)


class TokenYaniti(BaseModel):
    token: str
    token_turu: Literal["bearer"] = "bearer"
    hesap_id: uuid.UUID
    rol: str


class YetenekKartiOzeti(BaseModel):
    id: uuid.UUID
    rol_alani: str
    deneyim_seviyesi: str
    kanit_bekleyen: bool
    embedding_var: bool


class IhtiyacKartiOzeti(BaseModel):
    id: uuid.UUID
    problem_tanimi: str
    olusturma_tarihi: dt.datetime
    embedding_var: bool


class MeYaniti(BaseModel):
    """Giriş yapmış hesabın kendisi. Eskiden tarayıcıda tutulan "en son kartın /
    kurumun" kimliği (lib/yerel.ts) artık buradan geliyor."""

    hesap_id: uuid.UUID
    email: str
    rol: str
    # Genç için gencin adı, kurum için kurumun adı; GİRVAK'ın profili yok.
    ad: str | None
    kullanici_id: uuid.UUID | None = None
    kurum_id: uuid.UUID | None = None
    yetenek_kartlari: list[YetenekKartiOzeti] = Field(default_factory=list)
    ihtiyac_kartlari: list[IhtiyacKartiOzeti] = Field(default_factory=list)
    # Bildirimler Faz B'nin 5. adımında; o zamana kadar 0.
    okunmamis_bildirim: int = 0
