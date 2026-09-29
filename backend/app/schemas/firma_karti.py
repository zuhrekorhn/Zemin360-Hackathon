"""Firma kartı şemaları (docs/plans/firma-akisi.md § 0 karar 10, § 2, § 5).

`extra="forbid"`: tanınmayan alan sessizce yok sayılmaz, 422 döner.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict

from app.core.firma_karti import (
    ARANAN_EN_UZUN,
    NE_YAPIYORUZ_EN_UZUN,
    ONCEKI_ISLER_EN_UZUN,
    isbirligi_turlerini_temizle,
    uzun_metin,
    yetkinlikleri_temizle,
)


def _dolu(deger, mesaj: str):
    if not deger:
        raise ValueError(mesaj)
    return deger


NeYapiyoruz = Annotated[
    str | None, BeforeValidator(lambda v: uzun_metin(v, NE_YAPIYORUZ_EN_UZUN, "Açıklama"))
]
OncekiIsler = Annotated[
    str | None, BeforeValidator(lambda v: uzun_metin(v, ONCEKI_ISLER_EN_UZUN, "Önceki işler"))
]
Aranan = Annotated[
    str | None, BeforeValidator(lambda v: uzun_metin(v, ARANAN_EN_UZUN, "Aranan iş birliği"))
]
Yetkinlikler = Annotated[list[str], BeforeValidator(yetkinlikleri_temizle)]
IsbirligiTurleri = Annotated[list[str], BeforeValidator(isbirligi_turlerini_temizle)]


class FirmaKartiGirdisi(BaseModel):
    """Kartın tam hâli (sohbet onayı ve düzeltilmiş taslak)."""

    model_config = ConfigDict(extra="forbid")

    ne_yapiyoruz: Annotated[
        NeYapiyoruz, AfterValidator(lambda v: _dolu(v, "Firmanın ne yaptığı zorunlu"))
    ]
    yetkinlikler: Annotated[
        Yetkinlikler, AfterValidator(lambda v: _dolu(v, "En az bir yetkinlik zorunlu"))
    ]
    onceki_isler: OncekiIsler = None
    aranan_isbirligi: Aranan = None
    isbirligi_turleri: IsbirligiTurleri = []


class FirmaKartiGuncelleme(BaseModel):
    """`PATCH /kurum/kart`: yalnızca gönderilen alan değişir.

    Zorunlular (ne yapıyoruz, yetkinlikler) boşaltılamaz (422, uçta);
    isteğe bağlılar `null` ya da boş metinle silinir.
    """

    model_config = ConfigDict(extra="forbid")

    ne_yapiyoruz: NeYapiyoruz = None
    yetkinlikler: Yetkinlikler | None = None
    onceki_isler: OncekiIsler = None
    aranan_isbirligi: Aranan = None
    isbirligi_turleri: IsbirligiTurleri | None = None


class FirmaKartiYaniti(BaseModel):
    id: uuid.UUID
    kurum_id: uuid.UUID
    firma_adi: str
    ne_yapiyoruz: str
    yetkinlikler: list[str]
    onceki_isler: str | None
    aranan_isbirligi: str | None
    isbirligi_turleri: list[str]
    versiyon: int
    # Eşleştirmeye hazır mı (arka plan hazırlığı bitti mi)?
    embedding_var: bool
    olusturma_tarihi: dt.datetime
