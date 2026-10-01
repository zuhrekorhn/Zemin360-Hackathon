"""Erişim durumunun tespiti (plan § 5.2). Saf: ağ yok, kalıp tablosuyla test edilir.

Okunamayan (giriş duvarı, bot engeli, boş sayfa, ağ hatası) ile "yok" (404,
alan adı yok) ayrılır: ilki puanda "—", ikincisi 0.
"""

from __future__ import annotations

import httpx

from app.core.guvenli_istek import AdresBulunamadi, GuvensizAdres
from app.core.kanit_okuma.belge import ErisimDurumu

# Bu kadar kısa görünür metin "içerik okunamadı" sayılır (JavaScript ile çizilen sayfa).
EN_AZ_METIN = 200

_GIRIS_YOLLARI = (
    "/login",
    "/signin",
    "/sign-in",
    "/sign_in",
    "/authwall",
    "servicelogin",
    "accounts.google.com",
    "/accounts/login",
    "/giris",
    "/oturum-ac",
)
_GIRIS_BASLIKLARI = ("log in", "login", "sign in", "giriş yap", "oturum aç")
_BOT_ISARETLERI = (
    "attention required",
    "just a moment",
    "access denied",
    "verify you are human",
    "are you a robot",
    "captcha",
)


def erisim_durumu(
    *, durum: int, son_url: str, baslik: str | None, metin_uzunlugu: int
) -> ErisimDurumu:
    yol = son_url.lower()
    kucuk_baslik = (baslik or "").strip().lower()
    if durum in (404, 410):
        return ErisimDurumu.BULUNAMADI
    if durum == 401 or any(parca in yol for parca in _GIRIS_YOLLARI):
        return ErisimDurumu.GIRIS_GEREKLI
    if durum in (403, 429, 999) or any(isaret in kucuk_baslik for isaret in _BOT_ISARETLERI):
        return ErisimDurumu.ENGELLENDI
    if durum >= 400:
        return ErisimDurumu.HATA
    if kucuk_baslik.startswith(_GIRIS_BASLIKLARI):
        return ErisimDurumu.GIRIS_GEREKLI
    if metin_uzunlugu < EN_AZ_METIN:
        return ErisimDurumu.ICERIK_YOK
    return ErisimDurumu.ACIK


def hata_durumu(hata: Exception) -> ErisimDurumu:
    """İstek atılamadı ya da tamamlanamadı: nedenine göre durum."""
    if isinstance(hata, AdresBulunamadi):
        return ErisimDurumu.BULUNAMADI
    if isinstance(hata, GuvensizAdres):
        return ErisimDurumu.GUVENSIZ
    if isinstance(hata, httpx.HTTPError):
        return ErisimDurumu.HATA
    raise hata
