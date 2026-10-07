"""Gencin kayıt/profil alanlarının kuralları (docs/data-schema.md, § 5.1).

Saf fonksiyonlar: veritabanı yok. Şemalar (app/schemas/profil.py) bunları
doğrulayıcı olarak kullanır; /me de eksik alanları buradan sorar.

Toplanan yalnızca yapısal veri. Fotoğraf, yaş/doğum tarihi, cinsiyet, medeni
durum, TC kimlik no, adres ve ücret beklentisi BİLİNÇLİ OLARAK toplanmaz:
eşleştirme yalnızca yetkinliğe dayanıyor. Bu alanlar gönderilirse şema 422 döner.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from typing import Literal
from urllib.parse import urlsplit

from app.core.sehir import SEHIRLER, sehir_kanonik

OGRENCI = "ogrenci"
MEZUN = "mezun"
CALISIYOR = "calisiyor"

KARIYER_DURUMLARI: tuple[str, ...] = (OGRENCI, MEZUN, CALISIYOR)
KariyerDurumu = Literal["ogrenci", "mezun", "calisiyor"]

KARIYER_ETIKETLERI: dict[str, str] = {
    OGRENCI: "Öğrenci",
    MEZUN: "Mezun",
    CALISIYOR: "Çalışıyor",
}

# Hazırlık dahil lisans (6 yıllık bölümler) ve yüksek lisans için pay bırakıldı.
SINIF_EN_AZ, SINIF_EN_COK = 1, 8
MEZUNIYET_EN_ESKI = 1950
# Öğrenci beklenen mezuniyet yılını yazabilir.
MEZUNIYET_ILERI_YIL = 8
URL_EN_UZUN = 500
METIN_EN_UZUN = 200

# Profilde dolu olması gereken alanlar. Bu alanlardan önce açılmış hesaplarda
# boş olabilirler; panel engellemeyen bir bantla ister (docs/kararlar.md G10).
ZORUNLU_ALANLAR: tuple[str, ...] = (
    "sehir",
    "calisma_modelleri",
    "musaitlikler",
    "kariyer_durumu",
)


def sehir_dogrula(deger: str | None) -> str | None:
    """Katı: yalnızca 81 il, kanonik yazımda. Boş değer None.

    `sehir_kanonik` tanımadığı değeri kırpıp bırakıyor (sohbetten gelen serbest
    metin kaybolmasın diye); formda seçim listesi var, tanınmayan değer hatadır.
    """
    if deger is None or not deger.strip():
        return None
    kanonik = sehir_kanonik(deger)
    if kanonik not in SEHIRLER:
        raise ValueError(f"Tanınmayan şehir: {deger!r}. 81 ilden biri seçilmeli.")
    return kanonik


def mezuniyet_yili_dogrula(yil: int | None, bugun: dt.date | None = None) -> int | None:
    if yil is None:
        return None
    ust = (bugun or dt.date.today()).year + MEZUNIYET_ILERI_YIL
    if not MEZUNIYET_EN_ESKI <= yil <= ust:
        raise ValueError(f"Mezuniyet yılı {MEZUNIYET_EN_ESKI} ile {ust} arasında olmalı")
    return yil


def url_dogrula(deger: str | None) -> str | None:
    """http(s) adresi; şeması yoksa https:// eklenir. Boş değer None.

    Kullanıcılar "github.com/elif" diye yazıyor; bunu reddetmek yerine
    tamamlıyoruz (kanıt okumadaki `adresi_hazirla` ile aynı yaklaşım).
    """
    if deger is None or not deger.strip():
        return None
    adres = deger.strip()
    if len(adres) > URL_EN_UZUN:
        raise ValueError("Adres çok uzun")
    if "://" not in adres:
        adres = f"https://{adres.lstrip('/')}"
    parca = urlsplit(adres)
    alan_adi = parca.hostname or ""
    if parca.scheme not in ("http", "https") or "." not in alan_adi or " " in adres:
        raise ValueError("Geçerli bir web adresi değil (ör. https://github.com/kullanici)")
    return adres


def metin_temizle(deger: str | None) -> str | None:
    """Kısa serbest metin (okul, bölüm): boşsa None, uzunsa hata."""
    if deger is None or not deger.strip():
        return None
    metin = " ".join(deger.split())
    if len(metin) > METIN_EN_UZUN:
        raise ValueError(f"En çok {METIN_EN_UZUN} karakter")
    return metin


def eksik_profil_alanlari(
    *,
    sehir: str | None,
    calisma_modelleri: Sequence[str],
    musaitlikler: Sequence[str],
    kariyer_durumu: str | None,
) -> list[str]:
    """Doldurulması gereken zorunlu alanlar (sabit sırada)."""
    degerler = {
        "sehir": sehir,
        "calisma_modelleri": list(calisma_modelleri or []),
        "musaitlikler": list(musaitlikler or []),
        "kariyer_durumu": kariyer_durumu,
    }
    return [alan for alan in ZORUNLU_ALANLAR if not degerler[alan]]
