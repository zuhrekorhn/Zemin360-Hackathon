"""Türkçe metin karşılaştırma yardımcıları.

Türkçe'de büyük/küçük harf katlaması ASCII'den farklı ve Python'ın kendi
`lower()`'ı yanlış sonuç veriyor: `"İstanbul".lower()` → `'i̇stanbul'`
(i + U+0307). Bu yüzden katlama elle yapılıyor. Şehir karşılaştırması
(`app/core/sehir.py`) ve taslak birleştirme (`app/agents/sohbet_motoru.py`)
aynı kuralı paylaşsın diye burada duruyor.
"""

from __future__ import annotations

import unicodedata

from email_validator import EmailNotValidError, validate_email

# Türkçe'de büyük/küçük eşleniği ASCII'den farklı olan iki harf.
_BUYUK_ESLEME = str.maketrans({"I": "ı", "İ": "i"})
_BIRLESEN_NOKTA = "̇"


def turkce_kucult(metin: str) -> str:
    """Türkçe'ye duyarlı küçültme: I→ı, İ→i, sonra normal küçültme."""
    hazir = unicodedata.normalize("NFC", metin).translate(_BUYUK_ESLEME)
    return hazir.lower().replace(_BIRLESEN_NOKTA, "")


def eposta_normalize(eposta: str) -> str:
    """E-postayı karşılaştırılabilir biçime getirir: boşluk atılır, küçültülür.

    Kullanıcı ve kurum kaydı e-postayla bulunuyor ve e-posta UNIQUE.
    "Elif@Ornek.com" ile "elif@ornek.com" iki ayrı kayıt açmamalı. E-posta
    adresleri ASCII olduğu için burada düz `lower()` doğru (Türkçe katlama
    gerekmiyor).
    """
    return eposta.strip().lower()


def sade_anahtar(metin: str) -> str:
    """Karşılaştırma anahtarı: harf ve rakam dışındaki her şey atılır.

    "Team To Do" ile "Team ToDo" aynı işi anlatıyor; boşluk, tire ve noktalama
    farkı iki ayrı kayıt açmamalı.
    """
    kucuk = turkce_kucult(metin)
    return "".join(harf for harf in kucuk if harf.isalnum())


def gecerli_eposta(deger: str | None) -> str | None:
    """Geçerli e-posta ise normalize edilmiş hâli, değilse None (hoşgörülü okuma).

    Sohbetten çıkarılan referans e-postası gibi değerler için: geçersiz bir
    değer işi düşürmemeli, yalnızca atılmalı. Doğrulama pydantic'in EmailStr
    kuralıyla aynı (email-validator).
    """
    if not deger or not deger.strip():
        return None
    try:
        sonuc = validate_email(deger.strip(), check_deliverability=False)
    except EmailNotValidError:
        return None
    return eposta_normalize(sonuc.normalized)
