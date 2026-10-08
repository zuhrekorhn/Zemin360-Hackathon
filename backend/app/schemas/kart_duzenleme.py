"""Kart düzenleme şemaları (docs/agent-specs.md § 1).

Yalnızca gönderilen alan değişir (`model_fields_set`). `extra="forbid"`:
bilinmeyen alan sessizce yok sayılmaz.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.is_kalemi import IsTuru

DoluKisaMetin = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Metin = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Etiketler = Annotated[
    list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]],
    Field(max_length=30),
]
# Bir kartta en çok bu kadar çalışma: her çalışma güçlü modelle bir değerlendirme ve
# (referans verilirse) bir e-posta başlatır; sınırsız liste maliyet ve spam demek.
MAX_CALISMA = 20
DeneyimSeviyesi = Literal["potansiyel", "baslangic", "orta", "ileri"]


class Guclendirme(BaseModel):
    """'Kartını güçlendir' satırı: kanıtı eksik bir çalışma ve kanıtın etkisi."""

    somut_cikti_id: uuid.UUID
    baslik: str
    one_cikacagi_firsat: int
    metin: str


class KartGuncelleme(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rol_alani: DoluKisaMetin | None = None
    deneyim_seviyesi: DeneyimSeviyesi | None = None
    sektor_ilgi_alani: Etiketler | None = None
    araclar_teknolojiler: Etiketler | None = None
    sertifikalar: Etiketler | None = None
    diller: Etiketler | None = None


class IsKalemiGirdisi(BaseModel):
    """Formdan yeni iş kalemi. Link verilirse ilk kanıt parçası olur; referans kart
    sayfasının referans akışıyla eklenir."""

    model_config = ConfigDict(extra="forbid")

    baslik: DoluKisaMetin
    aciklama: Metin | None = None
    olculebilir_sonuc: Metin | None = None
    kendi_rolu: Metin | None = None
    kanit_linki: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = (
        None
    )
    is_turu: IsTuru | None = None


class IsKalemiGuncelleme(BaseModel):
    """Yalnızca gönderilen alan değişir; opsiyonel alan `null` ya da `""` ile silinir.

    Kanıt linki burada yok: kanıt parçaları kart sayfasının kanıt bölümünden
    (/dogrulama/kalem/{id}/kanit) eklenir ve kaldırılır.
    """

    model_config = ConfigDict(extra="forbid")

    baslik: DoluKisaMetin | None = None
    aciklama: Metin | None = None
    olculebilir_sonuc: Metin | None = None
    kendi_rolu: Metin | None = None
    is_turu: IsTuru | None = None
