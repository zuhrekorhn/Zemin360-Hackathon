"""Hesap bağlama şemaları (docs/dogrulama.md § 6)."""

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


class ProfilKoduYaniti(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    platform: str
    kod: str
    # Kodun aranacağı profil adresi (verilen adresten kurulur).
    profil_adresi: str
    son_gecerlilik: dt.datetime


class HesaplarimYaniti(BaseModel):
    hesaplar: list[BagliHesapYaniti]
    # Bugün açık olan OAuth sağlayıcıları (ayarı olmayan görünmez).
    oauth_saglayicilari: list[str]
    # Doğrulama koduyla bağlanabilen platformlar.
    profil_kodu_platformlari: list[str]
    # Süresi dolmamış, henüz doğrulanmamış kodlar.
    bekleyen_kodlar: list[ProfilKoduYaniti]
    # GİRVAK'ın elle doğrulamasını bekleyen platform (profil okunamadı).
    inceleme_bekleyen: str | None


class ProfilKoduIstegi(BaseModel):
    platform: str = Field(min_length=1, max_length=40)
    profil_adresi: str = Field(min_length=3, max_length=500)


class KodDogrulamaYaniti(BaseModel):
    # baglandi (201) | inceleme_bekliyor (202: profil okunamadı, GİRVAK bakacak)
    durum: str
    hesap: BagliHesapYaniti | None = None


class OAuthBaslatYaniti(BaseModel):
    yetki_adresi: str


class OAuthTamamlaIstegi(BaseModel):
    kod: str = Field(min_length=1, max_length=512)
    durum: str = Field(min_length=1, max_length=2048)
