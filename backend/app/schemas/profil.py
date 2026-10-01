"""Genç ve firma profil şemaları: kayıt formu ve profil düzenleme.

Genç: docs/plans/genc-akisi.md § 5.1. Firma: docs/plans/firma-akisi.md § 2.

`extra="forbid"`: toplanmayan bir alan (cinsiyet, doğum tarihi…) gönderilirse
sessizce yok sayılmaz, 422 döner — toplanmadığı açık olsun.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
)

from app.core import calisma_modeli
from app.core.firma_profili import (
    CalisanAraligi,
    FirmaTuru,
    kurulus_yili_dogrula,
    tanitim_temizle,
)
from app.core.genc_profili import (
    SINIF_EN_AZ,
    SINIF_EN_COK,
    KariyerDurumu,
    metin_temizle,
    mezuniyet_yili_dogrula,
    sehir_dogrula,
    url_dogrula,
)
from app.core.musaitlik import KatiMusaitlikler


def _calisma_modelleri_dogrula(degerler: object) -> list[str]:
    """Katı: her değer tanınmalı; sıra sabit, tekrarsız. (Onaydaki `temizle` hoşgörülü.)"""
    if degerler is None:
        return []
    if isinstance(degerler, str) or not isinstance(degerler, list | tuple):
        raise ValueError("Çalışma modeli bir liste olmalı")
    bilinmeyen = [d for d in degerler if not calisma_modeli.gecerli_mi(d)]
    if bilinmeyen:
        gecerliler = ", ".join(calisma_modeli.MODELLER)
        raise ValueError(f"Tanınmayan çalışma modeli: {bilinmeyen}. Geçerli: {gecerliler}")
    return calisma_modeli.temizle(degerler)


Sehir = Annotated[str | None, BeforeValidator(sehir_dogrula)]
CalismaModelleri = Annotated[list[str], BeforeValidator(_calisma_modelleri_dogrula)]
KisaMetin = Annotated[str | None, BeforeValidator(metin_temizle)]
WebAdresi = Annotated[str | None, BeforeValidator(url_dogrula)]
MezuniyetYili = Annotated[int | None, AfterValidator(mezuniyet_yili_dogrula)]
Sinif = Annotated[int | None, Field(ge=SINIF_EN_AZ, le=SINIF_EN_COK)]


def _dolu(deger, alan: str):
    if not deger:
        raise ValueError(f"{alan} zorunlu")
    return deger


class GencKayitProfili(BaseModel):
    """Kayıt formunun genç kısmı. Ad, e-posta, şifre `KayitIstegi`'nde."""

    model_config = ConfigDict(extra="forbid")

    sehir: Annotated[Sehir, AfterValidator(lambda v: _dolu(v, "Şehir"))]
    calisma_modelleri: Annotated[
        CalismaModelleri, AfterValidator(lambda v: _dolu(v, "En az bir çalışma modeli"))
    ]
    kariyer_durumu: KariyerDurumu
    musaitlikler: Annotated[
        KatiMusaitlikler, AfterValidator(lambda v: _dolu(v, "En az bir müsaitlik"))
    ]
    musaitlik_baslangici: dt.date | None = None
    okul: KisaMetin = None
    bolum: KisaMetin = None
    sinif: Sinif = None
    mezuniyet_yili: MezuniyetYili = None
    github_url: WebAdresi = None
    linkedin_url: WebAdresi = None
    portfolyo_url: WebAdresi = None


class GencProfilGuncelleme(BaseModel):
    """`PATCH /profil`: yalnızca gönderilen alan değişir.

    Zorunlu alanlar (şehir, çalışma modeli, müsaitlik, durum) boşaltılamaz;
    opsiyonel alanlar `null` ya da boş metinle silinir. `kvkk_onay: true`
    onay tarihi yoksa yazar (Faz öncesi hesaplar için); geri alma bu uçta yok.
    """

    model_config = ConfigDict(extra="forbid")

    ad: Annotated[str | None, BeforeValidator(metin_temizle)] = None
    sehir: Sehir = None
    calisma_modelleri: CalismaModelleri | None = None
    kariyer_durumu: KariyerDurumu | None = None
    musaitlikler: KatiMusaitlikler | None = None
    musaitlik_baslangici: dt.date | None = None
    okul: KisaMetin = None
    bolum: KisaMetin = None
    sinif: Sinif = None
    mezuniyet_yili: MezuniyetYili = None
    github_url: WebAdresi = None
    linkedin_url: WebAdresi = None
    portfolyo_url: WebAdresi = None
    kvkk_onay: bool | None = None


class GencProfilYaniti(BaseModel):
    ad: str
    email: str
    sehir: str | None
    calisma_modelleri: list[str]
    kariyer_durumu: str | None
    musaitlikler: list[str]
    musaitlik_baslangici: dt.date | None
    okul: str | None
    bolum: str | None
    sinif: int | None
    mezuniyet_yili: int | None
    github_url: str | None
    linkedin_url: str | None
    portfolyo_url: str | None
    kvkk_onay_tarihi: dt.datetime | None
    # Doldurulması gereken zorunlu alanlar (eski hesaplar için bant)
    eksik_alanlar: list[str]
    # Ad kilidi (dogrulama-iyilestirme.md § 6.3): e-posta doğrulanınca ad profilden
    # değişmez, talep GİRVAK'a gider. Bekleyen talebin istediği ad.
    ad_kilitli: bool = False
    bekleyen_ad: str | None = None


class AdDegisikligiIstegi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    yeni_ad: str = Field(min_length=1, max_length=100)
    gerekce: str | None = Field(default=None, max_length=300)

    @field_validator("yeni_ad")
    @classmethod
    def _ad_dolu(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Yeni ad boş olamaz.")
        return v

    @field_validator("gerekce")
    @classmethod
    def _gerekce_sade(cls, v: str | None) -> str | None:
        return " ".join(v.split()) or None if v is not None else None


# --- Firma (docs/plans/firma-akisi.md § 0 kararlar 1-2) ---------------------------------

KurulusYili = Annotated[int | None, AfterValidator(kurulus_yili_dogrula)]
Tanitim = Annotated[str | None, BeforeValidator(tanitim_temizle)]


class FirmaKayitProfili(BaseModel):
    """Kayıt formunun firma kısmı. Firma adı, e-posta, şifre `KayitIstegi`'nde."""

    model_config = ConfigDict(extra="forbid")

    tur: FirmaTuru
    sektor: Annotated[KisaMetin, AfterValidator(lambda v: _dolu(v, "Sektör"))]
    sehir: Annotated[Sehir, AfterValidator(lambda v: _dolu(v, "Şehir"))]
    web_sitesi: WebAdresi = None
    calisan_araligi: CalisanAraligi | None = None
    kurulus_yili: KurulusYili = None
    tanitim: Tanitim = None
    yetkili_ad: KisaMetin = None
    yetkili_gorev: KisaMetin = None


class FirmaProfilGuncelleme(BaseModel):
    """`PATCH /kurum/profil`: yalnızca gönderilen alan değişir.

    Zorunlu alanlar (ad, tür, sektör, şehir) boşaltılamaz; isteğe bağlılar
    `null` ya da boş metinle silinir. `kvkk_onay: true` onay tarihi yoksa yazar.
    """

    model_config = ConfigDict(extra="forbid")

    ad: KisaMetin = None
    tur: FirmaTuru | None = None
    sektor: KisaMetin = None
    sehir: Sehir = None
    web_sitesi: WebAdresi = None
    calisan_araligi: CalisanAraligi | None = None
    kurulus_yili: KurulusYili = None
    tanitim: Tanitim = None
    yetkili_ad: KisaMetin = None
    yetkili_gorev: KisaMetin = None
    kvkk_onay: bool | None = None


class FirmaProfilYaniti(BaseModel):
    # GİRVAK doğruladı mı? Bekliyor ile "şimdilik değil" firmaya ayrılmaz
    # (olumsuz haber nazik; firma "Doğrulama bekleniyor" görür).
    dogrulandi: bool = False
    ad: str
    email: str | None
    tur: str | None
    sektor: str | None
    sehir: str | None
    web_sitesi: str | None
    calisan_araligi: str | None
    kurulus_yili: int | None
    tanitim: str | None
    yetkili_ad: str | None
    yetkili_gorev: str | None
    kvkk_onay_tarihi: dt.datetime | None
    # Doldurulması gereken zorunlu alanlar (eski hesaplar için bant)
    eksik_alanlar: list[str]
