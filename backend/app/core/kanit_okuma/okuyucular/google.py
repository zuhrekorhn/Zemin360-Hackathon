"""Google Drive ve Docs: dışa aktarma adresleriyle içerik (docs/dogrulama.md § 5.6).

Paylaşımı "Bağlantıya sahip olan herkes" olmayan dosya giriş sayfasına yönlenir:
`GIRIS_GEREKLI` (gence paylaşım ayarı söylenir). Sunum ve Drive'daki PDF'lerin
içeriği dosya hattında okunur.
"""

from __future__ import annotations

import re

import httpx

from app.core.kanit_okuma.belge import KanitBelgesi
from app.core.kanit_okuma.erisim import hata_durumu
from app.core.kanit_okuma.istek import getir
from app.core.kanit_okuma.okuyucu import OkumaBaglami
from app.core.kanit_okuma.okuyucular.genel import sayfadan_belge

_DOCS = "https://docs.google.com"
_DONUSUMLER: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "drive.google.com",
        re.compile(r"/file/d/([\w-]+)"),
        "https://drive.usercontent.google.com/download?id={id}&export=download&confirm=t",
    ),
    (
        "docs.google.com",
        re.compile(r"/document/d/([\w-]+)"),
        _DOCS + "/document/d/{id}/export?format=txt",
    ),
    (
        "docs.google.com",
        re.compile(r"/spreadsheets/d/([\w-]+)"),
        _DOCS + "/spreadsheets/d/{id}/export?format=csv",
    ),
    (
        "docs.google.com",
        re.compile(r"/presentation/d/([\w-]+)"),
        _DOCS + "/presentation/d/{id}/export/pdf",
    ),
)


def disa_aktarma_adresi(url: httpx.URL) -> str | None:
    for alan, kalip, sablon in _DONUSUMLER:
        if url.host == alan and (eslesme := kalip.search(url.path)):
            return sablon.format(id=eslesme.group(1))
    return None


class GoogleOkuyucu:
    ad = "google"

    def uygun_mu(self, url: httpx.URL) -> bool:
        return disa_aktarma_adresi(url) is not None

    async def oku(self, url: httpx.URL, baglam: OkumaBaglami) -> KanitBelgesi:
        adres = disa_aktarma_adresi(url) or str(url)
        try:
            sayfa = await getir(adres, transport=baglam.transport)
        except Exception as hata:  # nedeni durum olur
            return KanitBelgesi(url=str(url), erisim=hata_durumu(hata), platform="google")
        return sayfadan_belge(str(url), sayfa, platform="google")
