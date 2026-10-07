"""Firma kartının alanları ve kuralları (docs/kararlar.md F3, F10).

Firma kartı, firmanın başka firmalara "biz bunu yapıyoruz" dediği karttır:
iş birliği ortağı arayan bir ilanın adayı olarak eşleştirmeye girer. Genç
arayan firmanın karta ihtiyacı yok (docs/kararlar.md F9).

Saf fonksiyonlar: veritabanı yok.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

ISBIRLIGI_TURLERI: tuple[str, ...] = ("pilot", "tedarik", "ortak_urun", "yatirim", "diger")
IsbirligiTuru = Literal["pilot", "tedarik", "ortak_urun", "yatirim", "diger"]

ISBIRLIGI_TURU_ETIKETLERI: dict[str, str] = {
    "pilot": "Pilot uygulama",
    "tedarik": "Tedarik",
    "ortak_urun": "Ortak ürün",
    "yatirim": "Yatırım",
    "diger": "Diğer",
}

NE_YAPIYORUZ_EN_UZUN = 1000
ONCEKI_ISLER_EN_UZUN = 1000
ARANAN_EN_UZUN = 500
YETKINLIK_EN_COK = 15
YETKINLIK_EN_UZUN = 80

# Onay için dolu olması gerekenler; sohbet bunları sorar (§ 5).
ZORUNLU_ALANLAR: tuple[str, ...] = ("ne_yapiyoruz", "yetkinlikler")


def uzun_metin(deger: str | None, en_uzun: int, alan: str) -> str | None:
    """Serbest metin: boşsa None, fazla boşluk tekilleşir, uzunsa hata."""
    if deger is None or not deger.strip():
        return None
    metin = " ".join(deger.split())
    if len(metin) > en_uzun:
        raise ValueError(f"{alan} en çok {en_uzun} karakter olmalı")
    return metin


def yetkinlikleri_temizle(degerler: Sequence[str] | None) -> list[str]:
    """Boşları atar, büyük/küçük harf duyarsız tekilleştirir, sırayı korur."""
    temiz: list[str] = []
    gorulen: set[str] = set()
    for deger in degerler or []:
        metin = " ".join(str(deger).split())
        if not metin:
            continue
        if len(metin) > YETKINLIK_EN_UZUN:
            raise ValueError(f"Bir yetkinlik en çok {YETKINLIK_EN_UZUN} karakter olmalı")
        anahtar = metin.casefold()
        if anahtar not in gorulen:
            gorulen.add(anahtar)
            temiz.append(metin)
    if len(temiz) > YETKINLIK_EN_COK:
        raise ValueError(f"En çok {YETKINLIK_EN_COK} yetkinlik yazılabilir")
    return temiz


def isbirligi_turlerini_temizle(degerler: Sequence[str] | None) -> list[str]:
    """Tanınmayanı reddeder; sıra `ISBIRLIGI_TURLERI`'ndeki gibi, tekrarsız."""
    secilen = set(degerler or [])
    bilinmeyen = secilen - set(ISBIRLIGI_TURLERI)
    if bilinmeyen:
        raise ValueError(f"Tanınmayan iş birliği türü: {sorted(bilinmeyen)}")
    return [tur for tur in ISBIRLIGI_TURLERI if tur in secilen]


def eksik_kart_alanlari(ne_yapiyoruz: str | None, yetkinlikler: Sequence[str]) -> list[str]:
    degerler = {"ne_yapiyoruz": ne_yapiyoruz, "yetkinlikler": list(yetkinlikler or [])}
    return [alan for alan in ZORUNLU_ALANLAR if not degerler[alan]]


# Embedding'i etkileyen alanlar: değişirse kart yeniden hazırlanır. `aranan_isbirligi`
# ve `isbirligi_turleri` firmanın ne aradığını söyler, ne yaptığını değil;
# benzerlik metnine girmez (docs/kararlar.md F5).
EMBEDDING_ALANLARI: frozenset[str] = frozenset({"ne_yapiyoruz", "yetkinlikler", "onceki_isler"})
