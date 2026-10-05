"""Tarayıcının tek ağ kapısı: SSRF süzgeçli vekil sunucu (proxy).

Chromium bu vekile bağlanır (`--proxy-server`, yerel adresler dahil, istisnasız);
kendi başına hiçbir yere bağlanamaz. Her bağlantıda hedef
`app.core.guvenli_istek.hedefi_dogrula` ile denetlenir (backend'le aynı kurallar:
yalnızca 80 / 443, alan adının bütün IP'leri genel internette) ve bağlantı
**denetlenen IP'ye** açılır: DNS yeniden bağlama kapalı. Yönlendirmeler, alt
kaynaklar ve WebSocket'ler de buradan geçtiği için her adım denetlenir.

Neden istek yakalama (`page.route`) değil: tarayıcı, yakalanmış bir isteğe
verilen 3xx yanıtını yakalamadan doğrudan ağdan izliyor; istekleri Python'dan
atmak da tarayıcının ağ kimliğini (TLS) kaybettirip bot engelini geri getiriyor.
HTTPS uçtan uca tarayıcıda kalır (CONNECT tüneli); vekil içeriği görmez.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable

from app.core.guvenli_istek import GuvensizAdres, hedefi_dogrula

logger = logging.getLogger("zemin360.yedek_okuyucu.vekil")

BASLIK_SINIRI = 64 * 1024
BAGLANTI_ZAMAN_ASIMI = 10

Baglan = Callable[[str, int], Awaitable[tuple[asyncio.StreamReader, asyncio.StreamWriter]]]


async def _ac(ip: str, port: int) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    return await asyncio.open_connection(ip, port)


def _istek_hedefi(yontem: str, hedef: str) -> tuple[str, str]:
    """İstek satırından denetlenecek adres ve gönderilecek yol.

    CONNECT `host:port` → (`https://host:port/`, ""); düz HTTP `http://host/yol`
    → (aynı adres, `/yol`)."""
    if yontem == "CONNECT":
        return f"https://{hedef}/", ""
    if not hedef.lower().startswith("http://"):
        raise GuvensizAdres("vekil yalnızca mutlak http adresi kabul eder")
    yol_baslangici = hedef.find("/", len("http://"))
    return hedef, (hedef[yol_baslangici:] if yol_baslangici != -1 else "/")


class SuzgecliVekil:
    """`127.0.0.1` üzerinde çalışan, yalnızca bu sürecin tarayıcısına açık vekil."""

    def __init__(self, baglan: Baglan = _ac) -> None:
        self._baglan = baglan
        self._sunucu: asyncio.Server | None = None
        self.port = 0

    async def baslat(self) -> None:
        self._sunucu = await asyncio.start_server(self._karsila, "127.0.0.1", 0)
        self.port = self._sunucu.sockets[0].getsockname()[1]

    async def durdur(self) -> None:
        if self._sunucu is not None:
            self._sunucu.close()
            await self._sunucu.wait_closed()

    async def _karsila(self, istemci_r: asyncio.StreamReader, istemci_w: asyncio.StreamWriter):
        try:
            await self._isle(istemci_r, istemci_w)
        except (ConnectionError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
            pass
        except Exception:  # bir bağlantının hatası vekili düşürmesin
            logger.exception("vekil baglantisi beklenmedik hatayla kapandi")
        finally:
            with contextlib.suppress(Exception):
                istemci_w.close()

    async def _isle(self, istemci_r: asyncio.StreamReader, istemci_w: asyncio.StreamWriter):
        bas = await istemci_r.readuntil(b"\r\n\r\n")
        if len(bas) > BASLIK_SINIRI:
            return await _reddet(istemci_w, 431)
        satirlar = bas.decode("latin-1").split("\r\n")
        try:
            yontem, hedef, surum = satirlar[0].split(" ", 2)
            adres, yol = _istek_hedefi(yontem.upper(), hedef)
            denetlenen = await hedefi_dogrula(adres)
        except (ValueError, GuvensizAdres) as hata:
            logger.info("vekil reddetti hedef=%s neden=%s", satirlar[0][:200], hata)
            return await _reddet(istemci_w, 403)
        port = denetlenen.url.port or (443 if denetlenen.url.scheme == "https" else 80)
        try:
            sunucu_r, sunucu_w = await asyncio.wait_for(
                self._baglan(str(denetlenen.ip), port), BAGLANTI_ZAMAN_ASIMI
            )
        except (OSError, TimeoutError):
            return await _reddet(istemci_w, 502)

        if yontem.upper() == "CONNECT":
            istemci_w.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await istemci_w.drain()
        else:
            # Düz HTTP: tek istek, sonra bağlantı kapanır (aynı bağlantıdan başka
            # bir sunucuya istek gelip denetimden kaçmasın).
            sunucu_w.write(_duz_istek(yontem, yol, surum, satirlar[1:]))
            await sunucu_w.drain()
        await _boru(istemci_r, istemci_w, sunucu_r, sunucu_w)


def _duz_istek(yontem: str, yol: str, surum: str, basliklar: list[str]) -> bytes:
    atilan = ("proxy-connection", "connection", "keep-alive", "proxy-authorization")
    kalan = [b for b in basliklar if b and not b.lower().startswith(atilan)]
    satirlar = [f"{yontem} {yol} {surum}", *kalan, "Connection: close", "", ""]
    return "\r\n".join(satirlar).encode("latin-1")


async def _reddet(yazici: asyncio.StreamWriter, durum: int) -> None:
    yazici.write(f"HTTP/1.1 {durum} Reddedildi\r\nContent-Length: 0\r\n\r\n".encode())
    with contextlib.suppress(ConnectionError):
        await yazici.drain()


async def _boru(
    istemci_r: asyncio.StreamReader,
    istemci_w: asyncio.StreamWriter,
    sunucu_r: asyncio.StreamReader,
    sunucu_w: asyncio.StreamWriter,
) -> None:
    async def aktar(okuyan: asyncio.StreamReader, yazan: asyncio.StreamWriter) -> None:
        try:
            while veri := await okuyan.read(65536):
                yazan.write(veri)
                await yazan.drain()
        except (ConnectionError, OSError):
            pass
        finally:
            with contextlib.suppress(Exception):
                yazan.close()

    await asyncio.gather(aktar(istemci_r, sunucu_w), aktar(sunucu_r, istemci_w))
