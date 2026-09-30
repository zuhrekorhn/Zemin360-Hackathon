"""Hata cümlelerinde alanların kullanıcıya görünen adları (docs/icerik-rehberi.md § 5.4).

Hata cümlesi veritabanı alan adı göstermez: "Bu alanlar boş bırakılamaz:
sehir" değil, "Şehir boş bırakılamaz." Adlar formdaki etiketlerle aynı.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

GENC_ALAN_ADLARI: dict[str, str] = {
    "ad": "Ad",
    "sehir": "Şehir",
    "calisma_modelleri": "Çalışma modeli",
    "musaitlikler": "Müsaitlik",
    "kariyer_durumu": "Durum",
}

FIRMA_ALAN_ADLARI: dict[str, str] = {
    "ad": "Firma adı",
    "tur": "Firma türü",
    "sektor": "Sektör",
    "sehir": "Şehir",
}

KART_ALAN_ADLARI: dict[str, str] = {
    "ne_yapiyoruz": "Ne yaptığınız",
    "yetkinlikler": "Yetkinlikler",
}


def bos_alan_mesaji(alanlar: Sequence[str], adlar: Mapping[str, str], *, siz: bool) -> str:
    """ "Şehir ve Durum boş bırakılamaz." Gence "sen", firmaya "siz" (yalnızca ikinci cümlede)."""
    etiketler = [adlar.get(alan, alan) for alan in alanlar]
    liste = (
        etiketler[0] if len(etiketler) == 1 else ", ".join(etiketler[:-1]) + " ve " + etiketler[-1]
    )
    ek = "Doldurup yeniden kaydedin." if siz else "Doldurup yeniden kaydet."
    return f"{liste} boş bırakılamaz. {ek}"
