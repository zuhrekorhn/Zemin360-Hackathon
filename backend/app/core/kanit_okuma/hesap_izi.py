"""Adresteki platform hesabı: `medium.com/@ayse/…` → (medium, ayse) (plan § 6).

Aynı bilgi iki yerde kullanılır: kanıtın kimin hesabında durduğunu bulmak
(sahiplik kuralı) ve profil kodu bağlamasında verilen profil adresinden
kullanıcı adını çıkarmak. Platform bilgisi tek yerde, bu tabloda; yeni
platform = `_KURALLAR`'a bir satır.

Tanınan bir platform alan adında hesap bulunamazsa (`dribbble.com/shots/…`)
iz yoktur; tanınmayan alan adı kişisel site sayılır (alan adının kendisi).
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum

import httpx

from app.core.kanit_okuma.belge import HesapIzi


class Saglayici(StrEnum):
    """Bağlanabilen hesap türleri (plan § 6.1)."""

    GITHUB = "github"
    GITLAB = "gitlab"
    ORCID = "orcid"
    YOUTUBE = "youtube"
    KAGGLE = "kaggle"
    BEHANCE = "behance"
    DRIBBBLE = "dribbble"
    MEDIUM = "medium"
    VIMEO = "vimeo"
    SOUNDCLOUD = "soundcloud"
    KISISEL_SITE = "kisisel_site"


# Platformların hesap olmayan ilk yol parçaları (sayfa, özellik, arama adresleri).
_GITHUB_DISI = frozenset(
    {"orgs", "settings", "topics", "search", "marketplace", "features", "sponsors", "about",
     "login", "explore", "collections", "trending", "apps", "pricing"}
)  # fmt: skip
_GITLAB_DISI = frozenset({"explore", "users", "help", "dashboard", "search", "-"})
_KAGGLE_ICERIK = frozenset({"code", "datasets", "models"})
_KAGGLE_DISI = frozenset(
    {"competitions", "learn", "discussions", "docs", "search", "c", "account", "settings"}
)
_BEHANCE_DISI = frozenset({"gallery", "search", "joblist", "galleries", "assets", "live"})
_DRIBBBLE_DISI = frozenset({"shots", "tags", "search", "jobs", "designers", "stories", "signup"})
_VIMEO_DISI = frozenset({"channels", "groups", "categories", "search", "watch", "features"})
_SOUNDCLOUD_DISI = frozenset({"discover", "search", "charts", "upload", "you", "pages"})


def _parcalar(url: httpx.URL) -> list[str]:
    return [p for p in url.path.split("/") if p]


def _ilk(disi: frozenset[str]) -> Callable[[list[str]], str | None]:
    """İlk yol parçası hesap adıdır (platformun kendi sayfaları dışında)."""

    def bul(parcalar: list[str]) -> str | None:
        return parcalar[0] if parcalar and parcalar[0].lower() not in disi else None

    return bul


def _youtube(parcalar: list[str]) -> str | None:
    if parcalar and parcalar[0].startswith("@"):
        return parcalar[0][1:]
    if len(parcalar) >= 2 and parcalar[0] in ("channel", "c", "user"):
        return parcalar[1]
    return None


def _medium(parcalar: list[str]) -> str | None:
    return parcalar[0][1:] if parcalar and parcalar[0].startswith("@") else None


def _kaggle(parcalar: list[str]) -> str | None:
    if len(parcalar) >= 2 and parcalar[0] in _KAGGLE_ICERIK:
        return parcalar[1]
    return _ilk(_KAGGLE_DISI | _KAGGLE_ICERIK)(parcalar)


def _vimeo(parcalar: list[str]) -> str | None:
    hesap = _ilk(_VIMEO_DISI)(parcalar)
    return hesap if hesap and not hesap.isdigit() else None  # vimeo.com/123 bir video


def _orcid(parcalar: list[str]) -> str | None:
    return parcalar[0] if parcalar and parcalar[0].count("-") == 3 else None


# alan adı → (sağlayıcı, yol parçalarından hesap adı)
_KURALLAR: dict[str, tuple[Saglayici, Callable[[list[str]], str | None]]] = {
    "github.com": (Saglayici.GITHUB, _ilk(_GITHUB_DISI)),
    "gitlab.com": (Saglayici.GITLAB, _ilk(_GITLAB_DISI)),
    "orcid.org": (Saglayici.ORCID, _orcid),
    "youtube.com": (Saglayici.YOUTUBE, _youtube),
    "kaggle.com": (Saglayici.KAGGLE, _kaggle),
    "behance.net": (Saglayici.BEHANCE, _ilk(_BEHANCE_DISI)),
    "dribbble.com": (Saglayici.DRIBBBLE, _ilk(_DRIBBBLE_DISI)),
    "medium.com": (Saglayici.MEDIUM, _medium),
    "vimeo.com": (Saglayici.VIMEO, _vimeo),
    "soundcloud.com": (Saglayici.SOUNDCLOUD, _ilk(_SOUNDCLOUD_DISI)),
}
# Hesabı yolda değil, yalnızca bu adreslerde bulunmayan platform alan adları.
_HESAPSIZ = frozenset({"youtu.be", "open.spotify.com", "figma.com", "drive.google.com",
                       "docs.google.com", "linkedin.com", "instagram.com", "x.com",
                       "twitter.com", "facebook.com"})  # fmt: skip


def alan_adi(url: httpx.URL) -> str:
    return url.host.lower().removeprefix("www.").removeprefix("m.")


def adresteki_hesap(adres: str | None) -> HesapIzi | None:
    """Adresin işaret ettiği hesap; tanınan platformda hesap yoksa None."""
    if not adres:
        return None
    try:
        url = httpx.URL(adres if "://" in adres else f"https://{adres}")
    except (httpx.InvalidURL, ValueError):
        return None
    alan = alan_adi(url)
    if not alan or "." not in alan:
        return None
    if alan.endswith(".medium.com"):  # ayse.medium.com
        return HesapIzi(Saglayici.MEDIUM, alan.removesuffix(".medium.com"))
    kural = _KURALLAR.get(alan)
    if kural is not None:
        saglayici, bul = kural
        hesap = bul(_parcalar(url))
        return HesapIzi(saglayici, hesap) if hesap else None
    if alan in _HESAPSIZ or alan.endswith(".google.com"):
        return None
    return HesapIzi(Saglayici.KISISEL_SITE, alan)
