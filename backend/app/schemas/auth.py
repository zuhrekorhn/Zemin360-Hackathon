"""Kayıt, giriş ve /me şemaları (docs/kimlik-ve-dongu.md § 1-2)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, StringConstraints, model_validator

from app.core.kimlik import SIFRE_EN_AZ
from app.schemas.profil import FirmaKayitProfili, GencKayitProfili

# Kayıttaki ad, referans e-postasının konusuna ve firmaya gösterilen kartın başlığına
# giriyor: tek satır ve kısa olmalı (satır sonu ya da çok uzun metinle oltalama
# cümlesi yazılamasın).
Ad = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
        pattern=r"^[^\r\n\t]+$",
    ),
]


class KayitIstegi(BaseModel):
    email: EmailStr
    # Üst sınır: argon2 uzun girdiyi işler ama sınırsız gövde bir DoS kapısı.
    sifre: str = Field(min_length=SIFRE_EN_AZ, max_length=256)
    # GİRVAK açık kayıtla açılamaz (not § 2): yalnızca betik/tohum veriyle.
    rol: Literal["genc", "kurum"]
    # Gencin adı ya da kurumun adı; profil bununla açılır.
    ad: Ad
    # Genç için zorunlu: kayıt formunun yapısal alanları (docs/kimlik-ve-dongu.md
    # § 2). Firma kaydı bunu göndermez.
    genc_profili: GencKayitProfili | None = None
    # Firma için zorunlu (docs/kararlar.md F2).
    firma_profili: FirmaKayitProfili | None = None
    # KVKK aydınlatma metni onayı; iki rol için de zorunlu. Sunucu onay anını yazar.
    kvkk_onay: bool = False

    @model_validator(mode="after")
    def _role_gore_zorunlular(self) -> KayitIstegi:
        if self.rol == "genc":
            if self.genc_profili is None:
                raise ValueError("Genç kaydında profil bilgileri zorunlu")
            if self.firma_profili is not None:
                raise ValueError("Genç kaydı firma profili taşımaz")
        else:
            if self.firma_profili is None:
                raise ValueError("Firma kaydında firma bilgileri zorunlu")
            if self.genc_profili is not None:
                raise ValueError("Kurum kaydı genç profili taşımaz")
        if not self.kvkk_onay:
            raise ValueError("KVKK aydınlatma metni onaylanmalı")
        return self


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
    # acik | kapandi (panel kapalı ilanı ayrı gösterir)
    durum: str = "acik"
    # genc | firma: hangi kapıdan açıldı
    aranan: str = "genc"
    # E-posta taslağı için (kurum e-postası değil).
    basari_kriteri: str | None = None


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
    # Gencin tek kartı (G17); Keşif'i tamamlamadıysa None.
    yetenek_karti: YetenekKartiOzeti | None = None
    ihtiyac_kartlari: list[IhtiyacKartiOzeti] = Field(default_factory=list)
    # Okunmamış bildirim sayısı (menüdeki rozet).
    okunmamis_bildirim: int = 0
    # Genç: doldurulması gereken zorunlu profil alanları ve KVKK onayı. Bu
    # alanlardan önce açılmış hesaplara panel engellemeyen bir bant gösterir.
    eksik_profil_alanlari: list[str] = Field(default_factory=list)
    kvkk_onayli: bool = True
    # Firma: firma kartı var mı? Yoksa panel "Firma kartınızı oluşturun" der (F9).
    firma_karti_var: bool = False
    # Kayıt e-postası doğrulandı mı (docs/dogrulama.md § 6.3). Doğrulanmamış
    # hesap her şeyi kullanır; menü bir uyarı ve "yeniden gönder" gösterir.
    eposta_dogrulandi: bool = False


class EpostaDogrulamaIstegi(BaseModel):
    token: str = Field(min_length=1, max_length=200)


class EpostaDogrulamaYaniti(BaseModel):
    eposta_dogrulandi: bool
