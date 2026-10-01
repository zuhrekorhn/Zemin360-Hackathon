"""Kanıt okuma: okuyucu zinciri (Strategy + Chain of Responsibility; plan § 5.1).

`kaniti_oku(adres)` adresi tanıyan ilk platform okuyucusunu dener; okuyamazsa
(`None`) sıradakine, en sonunda genel okuyucuya geçer. Her istek güvenli istek
katmanından geçer. Yeni platform: `okuyucular/` altında bir sınıf ve aşağıdaki
listeye bir satır.
"""

from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.kanit_okuma.belge import ErisimDurumu, KanitBelgesi
from app.core.kanit_okuma.istek import adresi_hazirla
from app.core.kanit_okuma.okuyucu import OkumaBaglami, Okuyucu
from app.core.kanit_okuma.okuyucular.genel import GenelOkuyucu
from app.core.kanit_okuma.okuyucular.github import GithubOkuyucu
from app.core.kanit_okuma.okuyucular.gitlab import GitlabOkuyucu
from app.core.kanit_okuma.okuyucular.google import GoogleOkuyucu
from app.core.kanit_okuma.okuyucular.medium import MediumOkuyucu
from app.core.kanit_okuma.okuyucular.oembed import OembedOkuyucu

PLATFORM_OKUYUCULARI: tuple[Okuyucu, ...] = (
    GithubOkuyucu(),
    GitlabOkuyucu(),
    OembedOkuyucu(),
    MediumOkuyucu(),
    GoogleOkuyucu(),
)
GENEL_OKUYUCU = GenelOkuyucu()


async def kaniti_oku(
    adres: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> KanitBelgesi:
    try:
        url = httpx.URL(adresi_hazirla(adres))
    except (httpx.InvalidURL, ValueError):
        return KanitBelgesi(url=adres, erisim=ErisimDurumu.GUVENSIZ)
    baglam = OkumaBaglami(transport=transport, github_token=get_settings().github_token)
    for okuyucu in PLATFORM_OKUYUCULARI:
        if okuyucu.uygun_mu(url):
            belge = await okuyucu.oku(url, baglam)
            if belge is not None:
                return belge
    return await GENEL_OKUYUCU.oku(url, baglam)
