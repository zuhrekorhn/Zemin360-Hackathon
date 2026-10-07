"""Firma doğrulaması: durumlar ve alan adı ipucu (docs/kararlar.md F6).

Sistem yalnızca **ipucu** verir, kararı GİRVAK verir. İpucu kayıt e-postasının
alan adıyla web sitesinin alan adını karşılaştırır; **siteye bağlanılmaz**, ağ
isteği yok (SSRF riski de yok). Saf fonksiyonlar; ipucu saklanmaz, okuma
anında hesaplanır.

Doğrulanmamış firma da platformu kullanır; yalnızca "Doğrulanmış firma"
işareti olmaz.
"""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit

BEKLIYOR = "bekliyor"
DOGRULANDI = "dogrulandi"
SIMDILIK_DEGIL = "simdilik_degil"

DOGRULAMA_DURUMLARI: tuple[str, ...] = (BEKLIYOR, DOGRULANDI, SIMDILIK_DEGIL)
GirvakKarari = Literal["dogrulandi", "simdilik_degil"]

UYUSUYOR = "uyusuyor"
UYUSMUYOR = "uyusmuyor"
UCRETSIZ_EPOSTA = "ucretsiz_eposta"
SITE_YOK = "site_yok"
EPOSTA_YOK = "eposta_yok"

AlanAdiIpucu = Literal["uyusuyor", "uyusmuyor", "ucretsiz_eposta", "site_yok", "eposta_yok"]

# Herkesin açabildiği e-posta sağlayıcıları: uzantı firmayı göstermez.
UCRETSIZ_SAGLAYICILAR = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "hotmail.com",
        "hotmail.com.tr",
        "outlook.com",
        "outlook.com.tr",
        "live.com",
        "msn.com",
        "yahoo.com",
        "yahoo.com.tr",
        "icloud.com",
        "me.com",
        "yandex.com",
        "yandex.com.tr",
        "proton.me",
        "protonmail.com",
        "mynet.com",
        "gmx.com",
        "aol.com",
    }
)


def _temiz(alan: str) -> str:
    alan = alan.strip().lower().rstrip(".")
    return alan[4:] if alan.startswith("www.") else alan


def eposta_alan_adi(eposta: str | None) -> str | None:
    if not eposta or "@" not in eposta:
        return None
    return _temiz(eposta.rsplit("@", 1)[1]) or None


def site_alan_adi(web_sitesi: str | None) -> str | None:
    if not web_sitesi or not web_sitesi.strip():
        return None
    adres = web_sitesi.strip()
    if "://" not in adres:
        adres = f"https://{adres}"
    return _temiz(urlsplit(adres).hostname or "") or None


def _ayni_firma(birinci: str, ikinci: str) -> bool:
    """Aynı alan adı ya da biri öbürünün alt alan adı (`ik.marketx.com` ↔ `marketx.com`)."""
    return birinci == ikinci or birinci.endswith(f".{ikinci}") or ikinci.endswith(f".{birinci}")


def alan_adi_ipucu(eposta: str | None, web_sitesi: str | None) -> str:
    """GİRVAK'a gösterilen ipucu; karar değil."""
    eposta_alani = eposta_alan_adi(eposta)
    if eposta_alani is None:
        return EPOSTA_YOK
    if eposta_alani in UCRETSIZ_SAGLAYICILAR:
        return UCRETSIZ_EPOSTA
    site = site_alan_adi(web_sitesi)
    if site is None:
        return SITE_YOK
    return UYUSUYOR if _ayni_firma(eposta_alani, site) else UYUSMUYOR


def dogrulama_sifirlanir_mi(oncesi: str | None, sonrasi: str | None) -> bool:
    """Web sitesi değişti mi? Değiştiyse GİRVAK'ın kararı yeniden beklenir (docs/kararlar.md F6).

    Karşılaştırma alan adı üzerinden: `https://marketx.com/` → `marketx.com` değişiklik değil.
    """
    return site_alan_adi(oncesi) != site_alan_adi(sonrasi)
