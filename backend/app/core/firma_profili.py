"""Firmanın kayıt/profil alanlarının kuralları (docs/plans/firma-akisi.md § 0 kararlar 1-2, § 2).

Saf fonksiyonlar: veritabanı yok. Şemalar (app/schemas/profil.py) bunları
doğrulayıcı olarak kullanır; /me de eksik alanları buradan sorar.

Vergi numarası, adres ve telefon BİLİNÇLİ OLARAK toplanmaz (karar 2, seçenek A):
kayıt kısa kalsın, hassas veri tutulmasın. Gönderilirse şema 422 döner.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

GIRISIM = "girisim"
KOBI = "kobi"
KURUMSAL = "kurumsal"

FIRMA_TURLERI: tuple[str, ...] = (GIRISIM, KOBI, KURUMSAL)
FirmaTuru = Literal["girisim", "kobi", "kurumsal"]

FIRMA_TURU_ETIKETLERI: dict[str, str] = {
    GIRISIM: "Girişim",
    KOBI: "KOBİ",
    KURUMSAL: "Kurumsal",
}

CALISAN_ARALIKLARI: tuple[str, ...] = ("1-10", "11-50", "51-250", "250+")
CalisanAraligi = Literal["1-10", "11-50", "51-250", "250+"]

KURULUS_EN_ESKI = 1900
TANITIM_EN_UZUN = 300

# Profilde dolu olması gereken alanlar. Bu alanlardan önce açılmış firma
# hesaplarında boş olabilirler; panel engellemeyen bir bantla ister (karar 9).
ZORUNLU_ALANLAR: tuple[str, ...] = ("tur", "sektor", "sehir")


def kurulus_yili_dogrula(yil: int | None, bugun: dt.date | None = None) -> int | None:
    if yil is None:
        return None
    ust = (bugun or dt.date.today()).year
    if not KURULUS_EN_ESKI <= yil <= ust:
        raise ValueError(f"Kuruluş yılı {KURULUS_EN_ESKI} ile {ust} arasında olmalı")
    return yil


def tanitim_temizle(deger: str | None) -> str | None:
    """Bir-iki cümlelik tanıtım: boşsa None, uzunsa hata. Satır sonları korunmaz."""
    if deger is None or not deger.strip():
        return None
    metin = " ".join(deger.split())
    if len(metin) > TANITIM_EN_UZUN:
        raise ValueError(f"Tanıtım en çok {TANITIM_EN_UZUN} karakter olmalı")
    return metin


def eksik_firma_alanlari(*, tur: str | None, sektor: str | None, sehir: str | None) -> list[str]:
    """Doldurulması gereken zorunlu alanlar (sabit sırada)."""
    degerler = {"tur": tur, "sektor": sektor, "sehir": sehir}
    return [alan for alan in ZORUNLU_ALANLAR if not degerler[alan]]
