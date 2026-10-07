"""Yedek okuyucu servisi (Playwright): arayüz, HTTP istemcisi ve kapalı kip (plan § 5.1, § 5.5).

Servis ayrı bir uygulamadır (`backend/yedek_okuyucu/`, ayrı süreç); sayfayı gerçek
bir tarayıcıda açar, işlenmiş HTML'i ve istenirse ekran görüntüsünü döner. Bizim
servisimiz olduğu için istek `guvenli_istek`'ten geçmez (iç adres); kullanıcının
adresini servis kendisi aynı kurallarla denetler.

Zarif düşüş (İ9): servis kapalıysa, ulaşılamıyorsa ya da sayfayı açamadıysa
`None` döner; okuyucu zinciri önceki okunuşla devam eder.
"""

from __future__ import annotations

import base64
import binascii
import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

import httpx

from app.core.dis_servisler.sarmalayicilar import gozlemli, zaman_asimli

logger = logging.getLogger("zemin360.yedek_okuyucu")


class EkranKurali(StrEnum):
    HER_ZAMAN = "her_zaman"
    # Görünür metin eşikten kısaysa
    METIN_AZSA = "metin_azsa"
    HAYIR = "hayir"


@dataclass(frozen=True)
class TarayiciSayfasi:
    # Ana çerçevenin son belgesinin HTTP durumu (bot doğrulaması geçildikten sonraki)
    durum: int
    son_url: str
    html: str
    # JPEG, sayfanın üstten en çok 3 parçası
    ekran_goruntuleri: tuple[bytes, ...] = ()


class YedekOkuyucu(Protocol):
    # "playwright" | "kapali"
    kip: str

    async def ac(
        self, url: str, *, ekran: EkranKurali, en_az_metin: int
    ) -> TarayiciSayfasi | None: ...


class PlaywrightYedekOkuyucu:
    kip = "playwright"

    def __init__(
        self,
        adres: str,
        anahtar: str,
        zaman_asimi_sn: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._adres = adres.rstrip("/")
        self._anahtar = anahtar
        self._zaman_asimi_sn = zaman_asimi_sn
        self._transport = transport
        self._iste = gozlemli("yedek_okuyucu")(zaman_asimli(zaman_asimi_sn)(self._servise_sor))

    async def ac(self, url: str, *, ekran: EkranKurali, en_az_metin: int) -> TarayiciSayfasi | None:
        try:
            yanit = await self._iste(url, ekran, en_az_metin)
        except Exception:  # zarif düşüş: gözlemli hatayı sağlığa ve log'a yazdı
            return None
        if yanit.get("hata") or yanit.get("durum") is None:
            # Sayfa açılamadı (güvensiz, bulunamadı, zaman aşımı): servis çalışıyor,
            # sayfa yedekle de okunamadı. Önceki okunuş geçerli.
            logger.info("yedek okuyucu sayfayi acamadi hata=%s", yanit.get("hata"))
            return None
        try:
            goruntuler = tuple(base64.b64decode(g) for g in yanit.get("ekran_goruntuleri") or [])
        except (binascii.Error, TypeError):
            goruntuler = ()
        return TarayiciSayfasi(
            durum=int(yanit["durum"]),
            son_url=str(yanit.get("son_url") or url),
            html=str(yanit.get("html") or ""),
            ekran_goruntuleri=goruntuler,
        )

    async def _servise_sor(self, url: str, ekran: EkranKurali, en_az_metin: int) -> dict:
        basliklar = {"Authorization": f"Bearer {self._anahtar}"} if self._anahtar else {}
        async with httpx.AsyncClient(
            timeout=self._zaman_asimi_sn, transport=self._transport
        ) as istemci:
            yanit = await istemci.post(
                f"{self._adres}/oku",
                json={"url": url, "ekran": ekran.value, "en_az_metin": en_az_metin},
                headers=basliklar,
            )
            yanit.raise_for_status()
            return yanit.json()


class KapaliYedekOkuyucu:
    """Null Object: yedek okuyucu yok, zincir önceki okunuşla biter."""

    kip = "kapali"

    async def ac(self, url: str, *, ekran: EkranKurali, en_az_metin: int) -> TarayiciSayfasi | None:
        return None
