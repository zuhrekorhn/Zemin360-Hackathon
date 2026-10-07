"""Kanıt adresine istek: güvenli istek katmanının üstünde, okuyucuların ortak kapısı.

Her istek `app/core/guvenli_istek.py`'den geçer (SSRF engeli; sabit API uç noktaları
dahil, tek kapı). Burada: gerçekçi tarayıcı başlıkları (bazı siteler tarayıcı kimliği
olmayan isteği 403 ile reddediyor), gövdenin en çok `EN_BUYUK_GOVDE`'ye
kadar akışla okunması ve metne çevrilmesi.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.guvenli_istek import guvenli_get

ZAMAN_ASIMI_SANIYE = 8
EN_BUYUK_GOVDE = 2_000_000

TARAYICI_BASLIKLARI: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}
_SEMA = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")


def adresi_hazirla(adres: str) -> str:
    """Şeması olmayan linke https:// ekler (genç linki çoğu zaman "github.com/…" yazıyor)."""
    link = adres.strip()
    return link if _SEMA.match(link) else f"https://{link.lstrip('/')}"


@dataclass(frozen=True)
class Sayfa:
    durum: int
    son_url: str
    icerik_turu: str
    govde: bytes

    @property
    def metin(self) -> str:
        eslesme = re.search(r"charset=([\w-]+)", self.icerik_turu, re.I)
        kodlama = eslesme.group(1) if eslesme else "utf-8"
        try:
            return self.govde.decode(kodlama, errors="replace")
        except LookupError:
            return self.govde.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.govde.decode("utf-8", errors="replace"))


async def getir(
    adres: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    basliklar: Mapping[str, str] | None = None,
    en_cok: int = EN_BUYUK_GOVDE,
) -> Sayfa:
    """Sayfayı getirir. `GuvensizAdres`, `AdresBulunamadi` ve `httpx.HTTPError` çağırana çıkar."""
    async with guvenli_get(
        adresi_hazirla(adres),
        zaman_asimi=ZAMAN_ASIMI_SANIYE,
        transport=transport,
        basliklar={**TARAYICI_BASLIKLARI, **(basliklar or {})},
    ) as yanit:
        parcalar: list[bytes] = []
        boyut = 0
        async for parca in yanit.aiter_bytes():
            parcalar.append(parca)
            boyut += len(parca)
            if boyut >= en_cok:
                break
        return Sayfa(
            durum=yanit.status_code,
            son_url=yanit.extensions.get("ozgun_url", adres),
            icerik_turu=yanit.headers.get("content-type", ""),
            govde=b"".join(parcalar)[:en_cok],
        )
