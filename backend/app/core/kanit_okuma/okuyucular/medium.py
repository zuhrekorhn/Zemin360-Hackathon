"""Medium yazısı: yazarın RSS akışından (sayfa Cloudflare engeline takılıyor; bulgu 3).

Akış yazarın son yazılarını içerir; aranan yazı akışta yoksa `None` (genel okuyucu
dener). Akış yalnızca medium.com'dan geldiği için XML güvenilir kaynaktandır.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from app.core.kanit_okuma.belge import ErisimDurumu, KanitBelgesi
from app.core.kanit_okuma.html_ozeti import html_ozeti
from app.core.kanit_okuma.istek import getir
from app.core.kanit_okuma.okuyucu import OkumaBaglami, metni_kur

_AD_ALANLARI = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def _akis_ve_kimlik(url: httpx.URL) -> tuple[str, str] | None:
    """(akış adresi, yazı kimliği): medium.com/@kisi/baslik-abc123 ya da kisi.medium.com/…"""
    parcalar = [p for p in url.path.split("/") if p]
    if not parcalar:
        return None
    kimlik = parcalar[-1].rsplit("-", 1)[-1]
    alan = url.host.removeprefix("www.")
    if alan == "medium.com" and parcalar[0].startswith("@") and len(parcalar) >= 2:
        return f"https://medium.com/feed/{parcalar[0]}", kimlik
    if alan.endswith(".medium.com"):
        return f"https://{alan}/feed", kimlik
    return None


class MediumOkuyucu:
    ad = "medium"

    def uygun_mu(self, url: httpx.URL) -> bool:
        return _akis_ve_kimlik(url) is not None

    async def oku(self, url: httpx.URL, baglam: OkumaBaglami) -> KanitBelgesi | None:
        bulunan = _akis_ve_kimlik(url)
        if bulunan is None:
            return None
        akis, kimlik = bulunan
        try:
            yanit = await getir(akis, transport=baglam.transport)
            if yanit.durum != 200:
                return None
            kok = ET.fromstring(yanit.govde)
        except (httpx.HTTPError, ET.ParseError):
            return None
        for oge in kok.iter("item"):
            if kimlik not in (oge.findtext("link") or ""):
                continue
            baslik = oge.findtext("title")
            yazar = oge.findtext("dc:creator", namespaces=_AD_ALANLARI)
            icerik = oge.findtext("content:encoded", namespaces=_AD_ALANLARI) or ""
            return KanitBelgesi(
                url=str(url),
                erisim=ErisimDurumu.ACIK,
                platform="medium",
                baslik=baslik,
                metin=metni_kur(
                    ("Başlık", baslik), ("Yazar", yazar), govde=html_ozeti(icerik).metin
                ),
                yazarlar=(yazar,) if yazar else (),
            )
        return None
