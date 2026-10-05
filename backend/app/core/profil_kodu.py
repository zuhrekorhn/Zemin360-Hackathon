"""Doğrulama koduyla hesap bağlama: platform stratejileri (plan § 6.1, § 6.2).

Genç profil açıklamasına `z360-xxxxxxxx` yazar; profil okunur, kod aranır. Her
platform bir `ProfilKoduPlatformu`'dur: verilen adresten kullanıcı adını çıkarır
ve okunacak profil adresini **kendisi kurar**. Kullanıcının adresi olduğu gibi
okunmaz: sorgu dizesindeki kod sayfada yankılanıp başkasının profilini
"doğrulatamasın". Kişisel sitede yalnızca ana sayfa okunur (alt sayfalardaki
yorumlar kod taşıyabilir).

Yeni platform = `kurulum.profil_kodu_platformlari`'na bir satır (sayfa okunan
platformlarda yalnızca adres şablonu). Bot engeline takılan ya da boş görünen
profil önce yedek okuyucuyla (tarayıcı) denenir; o da okuyamazsa GİRVAK'a gider.
"""

from __future__ import annotations

import re
import secrets
import string
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import quote

import httpx

from app.core.dis_servisler.yedek_okuyucu import (
    EkranKurali,
    KapaliYedekOkuyucu,
    YedekOkuyucu,
)
from app.core.guvenli_istek import GuvensizAdres
from app.core.kanit_okuma.belge import ErisimDurumu
from app.core.kanit_okuma.erisim import erisim_durumu, hata_durumu
from app.core.kanit_okuma.hesap_izi import Saglayici, adresteki_hesap
from app.core.kanit_okuma.html_ozeti import html_ozeti
from app.core.kanit_okuma.istek import Sayfa, getir

KOD_ONEKI = "z360-"
_KOD_ALFABESI = string.ascii_lowercase + string.digits


def kod_uret() -> str:
    return KOD_ONEKI + "".join(secrets.choice(_KOD_ALFABESI) for _ in range(8))


def kod_geciyor_mu(kod: str, metin: str) -> bool:
    """Kod ayrı bir sözcük olarak geçmeli (`z360-abc12345x` başka bir koddur)."""
    return re.search(rf"(?<![\w-]){re.escape(kod)}(?![\w-])", metin, re.IGNORECASE) is not None


@dataclass(frozen=True)
class Profil:
    platform: str
    kullanici_adi: str
    # Bağlantının tekil kimliği: küçük harfli ad (API değişmez kimlik verirse o).
    dis_kimlik: str
    # Bizim kurduğumuz, okunacak profil adresi.
    adres: str


@dataclass(frozen=True)
class ProfilOkumasi:
    erisim: ErisimDurumu
    # Kodun arandığı metin: başlık, meta açıklamaları ve sayfa metni.
    metin: str = ""
    # API'nin verdiği değişmez kimlik (YouTube kanal no); yoksa None.
    dis_kimlik: str | None = None


class ProfilKoduPlatformu(Protocol):
    platform: str

    def profil(self, adres: str) -> Profil | None: ...

    async def oku(
        self, profil: Profil, transport: httpx.AsyncBaseTransport | None = None
    ) -> ProfilOkumasi: ...


_YEDEKLENEN = frozenset({ErisimDurumu.ENGELLENDI, ErisimDurumu.ICERIK_YOK})


async def sayfayi_oku(
    adres: str,
    transport: httpx.AsyncBaseTransport | None = None,
    yedek: YedekOkuyucu | None = None,
) -> ProfilOkumasi:
    """Profil sayfasını okur. Kısa açıklamalı profil de okunmuş sayılır: kod
    başlıkta ya da meta açıklamasında olabilir (içerik uzunluğu şartı yok).
    Engellenen ya da boş görünen sayfa `yedek` ile (tarayıcıda) yeniden okunur."""
    try:
        okuma = _okuma(await getir(adres, transport=transport))
    except (GuvensizAdres, httpx.HTTPError) as hata:
        return ProfilOkumasi(hata_durumu(hata))
    if okuma.erisim not in _YEDEKLENEN or yedek is None:
        return okuma
    islenmis = await yedek.ac(adres, ekran=EkranKurali.HAYIR, en_az_metin=0)
    if islenmis is None:
        return okuma
    yeni = _okuma(
        Sayfa(islenmis.durum, islenmis.son_url, "text/html; charset=utf-8", islenmis.html.encode())
    )
    return yeni if yeni.erisim in (ErisimDurumu.ACIK, ErisimDurumu.ICERIK_YOK) else okuma


def _okuma(sayfa: Sayfa) -> ProfilOkumasi:
    ozet = html_ozeti(sayfa.metin)
    metin = "\n".join([ozet.gorunen_baslik or "", *ozet.meta.values(), ozet.metin]).strip()
    erisim = erisim_durumu(
        durum=sayfa.durum,
        son_url=sayfa.son_url,
        baslik=ozet.gorunen_baslik,
        metin_uzunlugu=len(metin),
    )
    return ProfilOkumasi(erisim, metin if erisim is not ErisimDurumu.BULUNAMADI else "")


@dataclass(frozen=True)
class SayfaPlatformu:
    """Profil sayfası okunan platform (Kaggle, Behance, Dribbble, Medium, Vimeo, SoundCloud)."""

    platform: str
    # `{ad}` kullanıcı adıyla doldurulur.
    sablon: str
    yedek: YedekOkuyucu = field(default_factory=KapaliYedekOkuyucu)

    def profil(self, adres: str) -> Profil | None:
        iz = adresteki_hesap(adres)
        if iz is None or iz.saglayici != self.platform:
            return None
        ad = iz.kullanici_adi
        return Profil(self.platform, ad, ad.casefold(), self.sablon.format(ad=quote(ad)))

    async def oku(
        self, profil: Profil, transport: httpx.AsyncBaseTransport | None = None
    ) -> ProfilOkumasi:
        return await sayfayi_oku(profil.adres, transport, self.yedek)


class KisiselSitePlatformu:
    platform = Saglayici.KISISEL_SITE.value

    def __init__(self, yedek: YedekOkuyucu | None = None) -> None:
        self.yedek = yedek or KapaliYedekOkuyucu()

    def profil(self, adres: str) -> Profil | None:
        iz = adresteki_hesap(adres)
        if iz is None or iz.saglayici != self.platform:
            return None
        return Profil(
            self.platform, iz.kullanici_adi, iz.kullanici_adi, f"https://{iz.kullanici_adi}/"
        )

    async def oku(
        self, profil: Profil, transport: httpx.AsyncBaseTransport | None = None
    ) -> ProfilOkumasi:
        return await sayfayi_oku(profil.adres, transport, self.yedek)


class YoutubePlatformu:
    """Kanal açıklaması. API anahtarı varsa YouTube Data API (kanal no da gelir),
    yoksa kanal sayfası (açıklama sayfanın meta açıklamasında)."""

    platform = Saglayici.YOUTUBE.value
    API = "https://www.googleapis.com/youtube/v3/channels"

    def __init__(self, api_anahtari: str = "", yedek: YedekOkuyucu | None = None) -> None:
        self._api_anahtari = api_anahtari
        self.yedek = yedek or KapaliYedekOkuyucu()

    def profil(self, adres: str) -> Profil | None:
        iz = adresteki_hesap(adres)
        if iz is None or iz.saglayici != self.platform:
            return None
        ad = iz.kullanici_adi
        kanal_no = ad.startswith("UC") and len(ad) == 24
        sayfa = (
            f"https://www.youtube.com/channel/{ad}"
            if kanal_no
            else f"https://www.youtube.com/@{ad}"
        )
        return Profil(self.platform, ad, ad if kanal_no else ad.casefold(), sayfa)

    async def oku(
        self, profil: Profil, transport: httpx.AsyncBaseTransport | None = None
    ) -> ProfilOkumasi:
        if not self._api_anahtari:
            return await sayfayi_oku(profil.adres, transport, self.yedek)
        kanal_no = profil.adres.startswith("https://www.youtube.com/channel/")
        sorgu = (
            f"id={quote(profil.kullanici_adi)}"
            if kanal_no
            else (f"forHandle=%40{quote(profil.kullanici_adi)}")
        )
        try:
            yanit = await getir(
                f"{self.API}?part=snippet&{sorgu}&key={self._api_anahtari}", transport=transport
            )
            ogeler = (yanit.json().get("items") or []) if yanit.durum == 200 else None
        except (GuvensizAdres, httpx.HTTPError, ValueError):
            ogeler = None
        if ogeler is None:
            # API arızası değerlendirmeyi düşürmez (İ9): sayfa yoluna düşülür.
            return await sayfayi_oku(profil.adres, transport, self.yedek)
        if not ogeler:
            return ProfilOkumasi(ErisimDurumu.BULUNAMADI)
        snippet = ogeler[0].get("snippet") or {}
        return ProfilOkumasi(
            ErisimDurumu.ACIK,
            f"{snippet.get('title', '')}\n{snippet.get('description', '')}",
            dis_kimlik=ogeler[0].get("id"),
        )


def sayfa_platformlari(yedek: YedekOkuyucu | None = None) -> tuple[SayfaPlatformu, ...]:
    yedek = yedek or KapaliYedekOkuyucu()
    sablonlar = (
        (Saglayici.KAGGLE, "https://www.kaggle.com/{ad}"),
        (Saglayici.BEHANCE, "https://www.behance.net/{ad}"),
        (Saglayici.DRIBBBLE, "https://dribbble.com/{ad}"),
        (Saglayici.MEDIUM, "https://medium.com/@{ad}"),
        (Saglayici.VIMEO, "https://vimeo.com/{ad}"),
        (Saglayici.SOUNDCLOUD, "https://soundcloud.com/{ad}"),
    )
    return tuple(SayfaPlatformu(s.value, sablon, yedek) for s, sablon in sablonlar)
