"""oEmbed: platformun resmî başlık ve yazar bilgisi (YouTube, Vimeo, SoundCloud, Spotify, Figma).

Slack ve LinkedIn'in link önizlemesiyle aynı yol: sayfanın kendisi yerine
platformun "bu içerik kimin" yanıtı. Büyük sayfayı indirmeye gerek kalmaz.
"""

from __future__ import annotations

from urllib.parse import quote

import httpx

from app.core.kanit_okuma.belge import ErisimDurumu, KanitBelgesi
from app.core.kanit_okuma.hesap_izi import adresteki_hesap
from app.core.kanit_okuma.istek import getir
from app.core.kanit_okuma.okuyucu import OkumaBaglami, metni_kur

_YOUTUBE = "https://www.youtube.com/oembed?format=json&url="
_FIGMA = "https://www.figma.com/api/oembed?url="
# (alan adı, yol öneki ya da None = her yol, uç nokta, platform)
_SAGLAYICILAR: tuple[tuple[str, str | None, str, str], ...] = (
    ("youtube.com", "/watch", _YOUTUBE, "youtube"),
    ("youtube.com", "/shorts/", _YOUTUBE, "youtube"),
    ("youtu.be", None, _YOUTUBE, "youtube"),
    ("vimeo.com", None, "https://vimeo.com/api/oembed.json?url=", "vimeo"),
    ("soundcloud.com", None, "https://soundcloud.com/oembed?format=json&url=", "soundcloud"),
    ("open.spotify.com", None, "https://open.spotify.com/oembed?url=", "spotify"),
    ("figma.com", "/file/", _FIGMA, "figma"),
    ("figma.com", "/design/", _FIGMA, "figma"),
)


def _saglayici(url: httpx.URL) -> tuple[str, str] | None:
    alan = url.host.removeprefix("www.").removeprefix("m.")
    for ad, onek, uc, platform in _SAGLAYICILAR:
        if alan == ad and (onek is None or url.path.startswith(onek)):
            return uc, platform
    return None


class OembedOkuyucu:
    ad = "oembed"

    def uygun_mu(self, url: httpx.URL) -> bool:
        return _saglayici(url) is not None

    async def oku(self, url: httpx.URL, baglam: OkumaBaglami) -> KanitBelgesi | None:
        saglayici = _saglayici(url)
        if saglayici is None:
            return None
        uc, platform = saglayici
        try:
            yanit = await getir(f"{uc}{quote(str(url), safe='')}", transport=baglam.transport)
            veri = yanit.json() if yanit.durum == 200 else None
        except (httpx.HTTPError, ValueError):
            return None
        if yanit.durum in (401, 403):
            return KanitBelgesi(url=str(url), erisim=ErisimDurumu.GIRIS_GEREKLI, platform=platform)
        if yanit.durum in (400, 404):
            return KanitBelgesi(url=str(url), erisim=ErisimDurumu.BULUNAMADI, platform=platform)
        if not isinstance(veri, dict):
            return None
        yazar = veri.get("author_name")
        return KanitBelgesi(
            url=str(url),
            erisim=ErisimDurumu.ACIK,
            platform=platform,
            baslik=veri.get("title"),
            metin=metni_kur(
                ("Platform", veri.get("provider_name") or platform),
                ("Başlık", veri.get("title")),
                ("Yazar", yazar),
                ("Yazar adresi", veri.get("author_url")),
            ),
            yazarlar=(yazar,) if yazar else (),
            # Yazar adresi kanalın / profilin kendisi: youtube.com/@kanal → (youtube, kanal).
            hesaplar=tuple(filter(None, [adresteki_hesap(veri.get("author_url"))])),
            veri={"yazar_adresi": veri.get("author_url")},
        )
