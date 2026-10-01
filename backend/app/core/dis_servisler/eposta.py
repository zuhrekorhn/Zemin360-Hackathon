"""E-posta gönderimi: arayüz, Resend adaptörü, log ve kapalı kip (plan § 14.4).

Servisler yalnızca `EpostaGonderici.gonder`'e bağlıdır; hangi sınıfın
kullanılacağına `kurulum.py` karar verir. Gönderim hatası akışı düşürmez
(İ9): `dusmeden_gonder` hatayı yutar, gözlem kaydına yazar, `False` döner.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.dis_servisler.sarmalayicilar import gozlemli, zaman_asimli

logger = logging.getLogger("zemin360.eposta")

RESEND_ADRESI = "https://api.resend.com/emails"


@dataclass(frozen=True)
class Eposta:
    alici: str
    konu: str
    metin: str


class EpostaGonderici(Protocol):
    # "resend" | "log" | "kapali": sağlık ucu ve log'lar için.
    kip: str

    async def gonder(self, eposta: Eposta) -> None: ...


class ResendGonderici:
    kip = "resend"

    def __init__(
        self,
        *,
        api_anahtari: str,
        gonderen: str,
        zaman_asimi_sn: float,
        tasima: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_anahtari = api_anahtari
        self._gonderen = gonderen
        self._tasima = tasima
        self.gonder = gozlemli("eposta")(zaman_asimli(zaman_asimi_sn)(self._gonder))

    async def _gonder(self, eposta: Eposta) -> None:
        async with httpx.AsyncClient(transport=self._tasima) as istemci:
            yanit = await istemci.post(
                RESEND_ADRESI,
                headers={"Authorization": f"Bearer {self._api_anahtari}"},
                json={
                    "from": self._gonderen,
                    "to": [eposta.alici],
                    "subject": eposta.konu,
                    "text": eposta.metin,
                },
            )
            yanit.raise_for_status()


class LogGonderici:
    """Yerel deneme: e-posta gönderilmez, içeriği log'a yazılır (bağlantı oradan açılır)."""

    kip = "log"

    async def gonder(self, eposta: Eposta) -> None:
        logger.info("eposta kip=log alici=%s konu=%s\n%s", eposta.alici, eposta.konu, eposta.metin)


class KapaliGonderici:
    """Null Object: e-posta özelliği kapalı; çağıran dal yazmaz."""

    kip = "kapali"

    async def gonder(self, eposta: Eposta) -> None:
        return None


async def dusmeden_gonder(gonderici: EpostaGonderici, eposta: Eposta) -> bool:
    """Gönderir; hata olursa log'a yazar ve `False` döner, akış sürer (İ9)."""
    try:
        await gonderici.gonder(eposta)
    except Exception:
        # Sağlık kaydına `gozlemli` yazdı; burada yalnızca bağlam.
        logger.exception("eposta gonderilemedi kip=%s konu=%s", gonderici.kip, eposta.konu)
        return False
    return True
