"""Keşif Ajanı uç noktalarının istek/yanıt şemaları (docs/api-contracts.md § Keşif)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class SomutCiktiTaslagi(BaseModel):
    baslik: str
    aciklama: str | None = None
    kanit_linki: str | None = None


class KartTaslagi(BaseModel):
    """Kullanıcıya onay için gösterilen taslak — henüz veritabanında değil."""

    rol_alani: str | None = None
    deneyim_seviyesi: str | None = None
    sektor_ilgi_alani: list[str] = Field(default_factory=list)
    araclar_teknolojiler: list[str] = Field(default_factory=list)
    somut_ciktilar: list[SomutCiktiTaslagi] = Field(default_factory=list)


class SohbetYaniti(BaseModel):
    oturum_id: uuid.UUID
    # Taslak hazırsa soru yok; kullanıcıdan beklenen şey onay.
    soru: str | None = None
    taslak: KartTaslagi
    taslak_hazir: bool


class SohbetBaslatIstegi(BaseModel):
    """Şimdilik gövde boş — oturum sunucuda açılır. Auth Faz 3'te gelecek."""


class SohbetCevapIstegi(BaseModel):
    oturum_id: uuid.UUID
    cevap: str = Field(min_length=1)


class KullaniciGirdisi(BaseModel):
    """Kart bir kullanıcıya bağlı (data-schema.md: YETENEK_KARTI.kullanici_id).

    Giriş/kayıt akışı Faz 3'te geleceği için kimlik şimdilik onay anında,
    e-postayla eşleştirilerek alınıyor.
    """

    ad: str
    email: EmailStr
    sehir: str | None = None
    musaitlik: str | None = None


class KartOnaylaIstegi(BaseModel):
    oturum_id: uuid.UUID
    kullanici: KullaniciGirdisi
    # Kullanıcı taslakta düzeltme yaptıysa son hali; yoksa sohbetteki taslak kaydedilir.
    duzeltilmis_taslak: KartTaslagi | None = None


class SomutCiktiYaniti(BaseModel):
    id: uuid.UUID
    baslik: str
    aciklama: str | None
    kanit_linki: str | None

    model_config = {"from_attributes": True}


class YetenekKartiYaniti(BaseModel):
    """Kartın dışarıya açılan hali.

    E-posta ve diğer iletişim bilgileri BURADA YOK — agent-specs.md § 1.5:
    iletişim bilgisi kuruma varsayılan olarak gösterilmez, iki taraf da
    onaylayınca açılır.
    """

    id: uuid.UUID
    rol_alani: str
    deneyim_seviyesi: str
    sektor_ilgi_alani: list[str]
    araclar_teknolojiler: list[str]
    kanit_bekleyen: bool
    versiyon: int
    embedding_var: bool
    somut_ciktilar: list[SomutCiktiYaniti]

    model_config = {"from_attributes": True}
