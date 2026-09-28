"""Gencin profil şemaları: kayıt formu ve profil düzenleme (docs/plans/genc-akisi.md § 5.1).

`extra="forbid"`: toplanmayan bir alan (cinsiyet, doğum tarihi…) gönderilirse
sessizce yok sayılmaz, 422 döner — toplanmadığı açık olsun.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field

from app.core import calisma_modeli
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
