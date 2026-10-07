"""E-posta gönderimi: arayüz, Resend adaptörü, log ve kapalı kip (docs/dogrulama.md § 14.4).

Servisler yalnızca `EpostaGonderici.gonder`'e bağlıdır; hangi sınıfın
kullanılacağına `kurulum.py` karar verir. Gönderim hatası akışı düşürmez
(İ9): `dusmeden_gonder` hatayı yutar, gözlem kaydına yazar, `False` döner.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from email.utils import parseaddr
from typing import Protocol

import httpx

from app.core.dis_servisler.sarmalayicilar import gozlemli, zaman_asimli

logger = logging.getLogger("zemin360.eposta")

RESEND_ADRESI = "https://api.resend.com/emails"
BREVO_ADRESI = "https://api.brevo.com/v3/smtp/email"


@dataclass(frozen=True)
class Eposta:
    alici: str
    konu: str
    metin: str
    # İsteğe bağlı; Brevo "to" alanında `name` olarak gider.
    alici_adi: str | None = None


class EpostaGonderici(Protocol):
    # "resend" | "brevo" | "log" | "kapali": sağlık ucu ve log'lar için.
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


class BrevoGonderici:
    """Brevo işlem e-postası API'si: alan adı gerekmez, doğrulanmış tek gönderen adresi yeter."""

    kip = "brevo"

    def __init__(
        self,
        *,
        api_anahtari: str,
        gonderen: str,
        zaman_asimi_sn: float,
        tasima: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_anahtari = api_anahtari
        # "Ad <adres>" ya da yalnızca "adres"; Brevo ad ve adresi ayrı alanlarda ister.
        ad, adres = parseaddr(gonderen)
        self._gonderen = {"email": adres, **({"name": ad} if ad else {})}
        self._tasima = tasima
        self.gonder = gozlemli("eposta")(zaman_asimli(zaman_asimi_sn)(self._gonder))

    async def _gonder(self, eposta: Eposta) -> None:
        alici = {"email": eposta.alici, **({"name": eposta.alici_adi} if eposta.alici_adi else {})}
        async with httpx.AsyncClient(transport=self._tasima) as istemci:
            yanit = await istemci.post(
                BREVO_ADRESI,
                headers={
                    "api-key": self._api_anahtari,
                    "content-type": "application/json",
                    "accept": "application/json",
                },
                json={
                    "sender": self._gonderen,
                    "to": [alici],
                    "subject": eposta.konu,
                    "textContent": eposta.metin,
                },
            )
        if yanit.status_code >= 400:
            # Brevo'nun hata mesajı log'a yazılır; api-key ve alıcı adresi yazılmaz.
            mesaj = self._temiz_mesaj(yanit, eposta.alici)
            logger.error("brevo hatasi durum=%s mesaj=%s", yanit.status_code, mesaj)
            raise BrevoHatasi(f"brevo {yanit.status_code}")
        # Başarıda log'a yalnızca messageId.
        logger.info("eposta gonderildi kip=brevo messageId=%s", _mesaj_kimligi(yanit))

    def _temiz_mesaj(self, yanit: httpx.Response, alici: str) -> str:
        try:
            govde = yanit.json()
            metin = str(govde.get("message") or govde) if isinstance(govde, dict) else str(govde)
        except ValueError:
            metin = yanit.text
        for gizli, yerine in ((self._api_anahtari, "[anahtar]"), (alici, "[alici]")):
            if gizli:
                metin = re.sub(re.escape(gizli), yerine, metin, flags=re.IGNORECASE)
        return metin[:300]


class BrevoHatasi(Exception):
    """Brevo 4xx/5xx döndü. Mesaj yalnızca durum kodu: ayrıntı (Brevo'nun mesajı) log'da."""


def _mesaj_kimligi(yanit: httpx.Response) -> str | None:
    try:
        govde = yanit.json()
    except ValueError:
        return None
    return govde.get("messageId") if isinstance(govde, dict) else None


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


# Belgeler ve deneme için ayrılmış alan adları (RFC 2606): bu adreslere posta gitmez, gerçek
# sağlayıcıya göndermek hata ya da sıçrama (bounce) olur ve gönderen itibarını bozar.
SAHTE_UZANTILAR = (".example", ".test", ".invalid", ".localhost")
SAHTE_ALAN_ADLARI = ("example.com", "example.org", "example.net")


def sahte_adres_mi(adres: str) -> bool:
    alan = adres.rsplit("@", 1)[-1].strip().lower().rstrip(".")
    return alan in SAHTE_ALAN_ADLARI or alan.endswith(SAHTE_UZANTILAR)


class SahteAdresiAtlayan:
    """Gerçek gönderici sınıfını sarar: `.example` gibi adreslere ağ isteği atmaz, log'a yazar.

    Demo hesapları (`.example`) için gönderim hata sayılmaz, akış ve testler aynı kalır.
    Log kipi sarılmaz: orada zaten ağ isteği yok, içerik log'a yazılıyor.
    """

    def __init__(self, ic: EpostaGonderici) -> None:
        self.ic = ic

    @property
    def kip(self) -> str:
        return self.ic.kip

    async def gonder(self, eposta: Eposta) -> None:
        if sahte_adres_mi(eposta.alici):
            logger.info("eposta atlandi (sahte adres) kip=%s konu=%s", self.ic.kip, eposta.konu)
            return
        await self.ic.gonder(eposta)


async def dusmeden_gonder(gonderici: EpostaGonderici, eposta: Eposta) -> bool:
    """Gönderir; hata olursa log'a yazar ve `False` döner, akış sürer (İ9)."""
    try:
        await gonderici.gonder(eposta)
    except Exception:
        # Sağlık kaydına `gozlemli` yazdı; burada yalnızca bağlam.
        logger.exception("eposta gonderilemedi kip=%s konu=%s", gonderici.kip, eposta.konu)
        return False
    return True
