"""Türkçe metin karşılaştırma yardımcıları.

Türkçe'de büyük/küçük harf katlaması ASCII'den farklı ve Python'ın kendi
`lower()`'ı yanlış sonuç veriyor: `"İstanbul".lower()` → `'i̇stanbul'`
(i + U+0307). Bu yüzden katlama elle yapılıyor. Şehir karşılaştırması
(`app/core/sehir.py`) ve taslak birleştirme (`app/agents/sohbet_motoru.py`)
aynı kuralı paylaşsın diye burada duruyor.
"""

from __future__ import annotations

import unicodedata

# Türkçe'de büyük/küçük eşleniği ASCII'den farklı olan iki harf.
_BUYUK_ESLEME = str.maketrans({"I": "ı", "İ": "i"})
_BIRLESEN_NOKTA = "̇"


def turkce_kucult(metin: str) -> str:
    """Türkçe'ye duyarlı küçültme: I→ı, İ→i, sonra normal küçültme."""
    hazir = unicodedata.normalize("NFC", metin).translate(_BUYUK_ESLEME)
    return hazir.lower().replace(_BIRLESEN_NOKTA, "")


def sade_anahtar(metin: str) -> str:
    """Karşılaştırma anahtarı: harf ve rakam dışındaki her şey atılır.

    "Team To Do" ile "Team ToDo" aynı işi anlatıyor; boşluk, tire ve noktalama
    farkı iki ayrı kayıt açmamalı.
    """
    kucuk = turkce_kucult(metin)
    return "".join(harf for harf in kucuk if harf.isalnum())
