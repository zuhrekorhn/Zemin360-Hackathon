"""Üçüncü taraf sayfa okuma servisi: arayüz, Jina Reader ve kapalı kip (docs/dogrulama.md § 5.1,
§ 14.4).

Zincirin son basamağı: yalnızca bayrak açıksa (`UZAK_OKUYUCU=jina`, varsayılan
kapalı) ve kendi yedek okuyucumuz (Playwright) sayfayı okuyamadıysa çağrılır.
Linkin adresi yurt dışındaki bir servise gider; KVKK aydınlatma metninde listelidir.
Sabit API ucu da `guvenli_istek`'ten geçer (tek kapı, § 5.3).

Zarif düşüş (İ9): servis hata verir ya da sayfayı okuyamazsa `None`.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.dis_servisler.sarmalayicilar import gozlemli, zaman_asimli
from app.core.guvenli_istek import guvenli_get

logger = logging.getLogger("zemin360.uzak_okuyucu")

EN_BUYUK_YANIT = 2_000_000


@dataclass(frozen=True)
class UzakSayfa:
    baslik: str | None
    metin: str
    son_url: str


class UzakOkuyucu(Protocol):
    # "jina" | "kapali"
    kip: str

    async def oku(self, url: str) -> UzakSayfa | None: ...


class JinaOkuyucu:
    kip = "jina"
    ADRES = "https://r.jina.ai/"

    def __init__(
        self,
        api_anahtari: str,
        zaman_asimi_sn: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_anahtari = api_anahtari
        self._zaman_asimi_sn = zaman_asimi_sn
        self._transport = transport
        self._iste = gozlemli("uzak_okuyucu")(zaman_asimli(zaman_asimi_sn)(self._servise_sor))

    async def oku(self, url: str) -> UzakSayfa | None:
        try:
            yanit = await self._iste(url)
        except Exception:  # zarif düşüş: gözlemli hatayı sağlığa ve log'a yazdı
            return None
        veri = yanit.get("data") if isinstance(yanit, dict) else None
        if not isinstance(veri, dict) or not str(veri.get("content") or "").strip():
            return None
        return UzakSayfa(
            baslik=(str(veri.get("title")).strip() or None) if veri.get("title") else None,
            metin=str(veri["content"]).strip(),
            son_url=str(veri.get("url") or url),
        )

    async def _servise_sor(self, url: str) -> dict:
        basliklar = {"Accept": "application/json", "X-Return-Format": "text"}
        if self._api_anahtari:
            basliklar["Authorization"] = f"Bearer {self._api_anahtari}"
        async with guvenli_get(
            f"{self.ADRES}{url}",
            zaman_asimi=self._zaman_asimi_sn,
            transport=self._transport,
            basliklar=basliklar,
        ) as yanit:
            if yanit.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"Jina {yanit.status_code}", request=yanit.request, response=yanit
                )
            govde = b""
            async for parca in yanit.aiter_bytes():
                govde += parca
                if len(govde) >= EN_BUYUK_YANIT:
                    break
        return json.loads(govde[:EN_BUYUK_YANIT].decode("utf-8", errors="replace"))


class KapaliUzakOkuyucu:
    """Null Object: üçüncü taraf okuma yok (varsayılan)."""

    kip = "kapali"

    async def oku(self, url: str) -> UzakSayfa | None:
        return None
