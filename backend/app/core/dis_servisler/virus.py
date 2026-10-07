"""Yüklenen dosyada zararlı içerik taraması: arayüz, ClamAV ve kapalı kip (docs/dogrulama.md § 4.4).

ClamAV ayrı bir konteynerde çalışır; `clamd`'nin INSTREAM komutu TCP üzerinden
kullanılır (ek kütüphane yok). Tarayıcı kapalıysa ya da hata verirse dosya
yine kabul edilir (bilinçli karar): PDF temizliği ve görselin yeniden
kodlanması her durumda çalışır, dosya yalnızca indirme olarak sunulur;
taranmadığı sağlık ucunda ve log'da görünür. Yalnızca "zararlı" sonucu reddeder.
"""

from __future__ import annotations

import asyncio
import logging
import struct
from enum import StrEnum
from typing import Protocol

from app.core.dis_servisler.sarmalayicilar import gozlemli, zaman_asimli

logger = logging.getLogger("zemin360.virus")

_PARCA = 64 * 1024


class TaramaSonucu(StrEnum):
    TEMIZ = "temiz"
    ZARARLI = "zararli"
    # Tarayıcı kapalı ya da ulaşılamadı: dosya kabul edilir (bkz. modül notu).
    TARANMADI = "taranmadi"


class VirusTarayici(Protocol):
    # "clamav" | "kapali"
    kip: str

    async def tara(self, veri: bytes) -> TaramaSonucu: ...


def clamd_yanitini_coz(yanit: bytes) -> TaramaSonucu:
    metin = yanit.rstrip(b"\0\n").decode(errors="replace")
    if metin.endswith("OK"):
        return TaramaSonucu.TEMIZ
    if metin.endswith("FOUND"):
        return TaramaSonucu.ZARARLI
    raise RuntimeError(f"clamd yanıtı anlaşılamadı: {metin[:80]}")


class ClamavTarayici:
    kip = "clamav"

    def __init__(self, sunucu: str, port: int, zaman_asimi_sn: float) -> None:
        self._sunucu = sunucu
        self._port = port
        self._tara = gozlemli("virus")(zaman_asimli(zaman_asimi_sn)(self._clamd))

    async def tara(self, veri: bytes) -> TaramaSonucu:
        try:
            return await self._tara(veri)
        except Exception:  # zarif düşüş (İ9): gözlemli hatayı sağlığa yazdı
            logger.warning("virus taramasi yapilamadi; dosya taranmadan kabul edildi")
            return TaramaSonucu.TARANMADI

    async def _clamd(self, veri: bytes) -> TaramaSonucu:
        okuyucu, yazici = await asyncio.open_connection(self._sunucu, self._port)
        try:
            yazici.write(b"zINSTREAM\0")
            for i in range(0, len(veri), _PARCA):
                parca = veri[i : i + _PARCA]
                yazici.write(struct.pack("!L", len(parca)) + parca)
            yazici.write(struct.pack("!L", 0))
            await yazici.drain()
            return clamd_yanitini_coz(await okuyucu.read(4096))
        finally:
            yazici.close()


class KapaliTarayici:
    """Null Object: tarama yok, dosya kabul edilir."""

    kip = "kapali"

    async def tara(self, veri: bytes) -> TaramaSonucu:
        return TaramaSonucu.TARANMADI
