"""Yedek okuyucu servisi (docs/dogrulama.md § 5.5): süzgeçli vekil ve tarayıcının ağ kapısı.

Vekil testleri ağa çıkmaz: çözümleyici sahte, bağlantı yerel bir sunucuya
yönlendirilir. Tarayıcı testi Chromium kuruluysa çalışır (yoksa atlanır).
"""

from __future__ import annotations

import asyncio
import ipaddress

import pytest

from app.core import guvenli_istek
from yedek_okuyucu.vekil import SuzgecliVekil, _istek_hedefi

GENEL_IP = "93.184.216.34"


@pytest.fixture
def sahte_dns(monkeypatch):
    async def coz(host: str, port: int):
        if host == "ornek.test":
            return [ipaddress.ip_address(GENEL_IP)]
        if host == "ic.test":
            return [ipaddress.ip_address("10.0.0.5")]
        raise OSError("çözülemedi")

    monkeypatch.setattr(guvenli_istek, "cozumleyici", coz)


class _YerelSunucu:
    """Vekilin bağlandığı "uzak" sunucu: gelen ilk isteği kaydeder, sabit yanıt döner."""

    def __init__(self, yanit: bytes = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok") -> None:
        self.yanit = yanit
        self.gelenler: list[bytes] = []
        self.port = 0

    async def __aenter__(self):
        self._sunucu = await asyncio.start_server(self._isle, "127.0.0.1", 0)
        self.port = self._sunucu.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, *_):
        self._sunucu.close()
        await self._sunucu.wait_closed()

    async def _isle(self, okuyucu, yazici):
        self.gelenler.append(await okuyucu.readuntil(b"\r\n\r\n"))
        yazici.write(self.yanit)
        await yazici.drain()
        yazici.close()


async def _vekile_gonder(vekil: SuzgecliVekil, istek: bytes) -> bytes:
    okuyucu, yazici = await asyncio.open_connection("127.0.0.1", vekil.port)
    yazici.write(istek)
    await yazici.drain()
    yanit = await asyncio.wait_for(okuyucu.read(4096), 5)
    yazici.close()
    return yanit


def _calistir(istek: bytes, sunucu_yaniti: bytes | None = None) -> tuple[bytes, list[bytes], list]:
    """Vekili kurar, isteği gönderir; (vekilin yanıtı, sunucuya gelenler, bağlanılan hedefler)."""
    hedefler: list[tuple[str, int]] = []

    async def calistir():
        async with _YerelSunucu(*([sunucu_yaniti] if sunucu_yaniti else [])) as sunucu:

            async def baglan(ip: str, port: int):
                hedefler.append((ip, port))
                return await asyncio.open_connection("127.0.0.1", sunucu.port)

            vekil = SuzgecliVekil(baglan)
            await vekil.baslat()
            try:
                yanit = await _vekile_gonder(vekil, istek)
                await asyncio.sleep(0.05)
            finally:
                await vekil.durdur()
            return yanit, sunucu.gelenler

    yanit, gelenler = asyncio.run(calistir())
    return yanit, gelenler, hedefler


@pytest.mark.parametrize(
    ("satir", "beklenen"),
    [
        ("CONNECT 127.0.0.1:443 HTTP/1.1", "loopback"),
        ("CONNECT 169.254.169.254:80 HTTP/1.1", "bulut kimlik servisi"),
        ("CONNECT ic.test:443 HTTP/1.1", "iç ağa çözülen ad"),
        ("CONNECT ornek.test:22 HTTP/1.1", "izinsiz port"),
        ("GET http://localhost:8000/ HTTP/1.1", "düz HTTP ile yerel"),
        ("GET /goreli HTTP/1.1", "mutlak olmayan adres"),
        ("GET ftp://ornek.test/ HTTP/1.1", "http olmayan şema"),
        ("CONNECT yok.test:443 HTTP/1.1", "çözülemeyen ad"),
    ],
)
def test_vekil_kural_disi_hedefi_reddeder_ve_baglanmaz(sahte_dns, satir, beklenen):
    yanit, gelenler, hedefler = _calistir(f"{satir}\r\nHost: x\r\n\r\n".encode())
    assert yanit.startswith(b"HTTP/1.1 403"), beklenen
    assert hedefler == [] and gelenler == []


def test_connect_denetlenen_ipye_tunel_acar(sahte_dns):
    istek = b"CONNECT ornek.test:443 HTTP/1.1\r\nHost: ornek.test:443\r\n\r\nTUNEL-ICI\r\n\r\n"
    yanit, gelenler, hedefler = _calistir(istek)
    assert yanit.startswith(b"HTTP/1.1 200 Connection Established")
    # Bağlantı alan adına değil denetlenen IP'ye: DNS yeniden bağlama kapalı.
    assert hedefler == [(GENEL_IP, 443)]
    assert gelenler == [b"TUNEL-ICI\r\n\r\n"]


def test_duz_http_tek_istek_olarak_iletilir(sahte_dns):
    istek = (
        b"GET http://ornek.test/proje?x=1 HTTP/1.1\r\nHost: ornek.test\r\n"
        b"Proxy-Connection: keep-alive\r\nAccept: text/html\r\n\r\n"
    )
    yanit, gelenler, hedefler = _calistir(istek)
    assert yanit.endswith(b"ok")
    assert hedefler == [(GENEL_IP, 80)]
    ilk = gelenler[0].decode()
    assert ilk.startswith("GET /proje?x=1 HTTP/1.1\r\n")
    assert "Proxy-Connection" not in ilk and "Accept: text/html" in ilk
    # Aynı bağlantıdan başka bir sunucuya ikinci istek gelemesin.
    assert "Connection: close" in ilk


def test_istek_hedefi():
    assert _istek_hedefi("CONNECT", "ornek.test:443") == ("https://ornek.test:443/", "")
    assert _istek_hedefi("GET", "http://ornek.test") == ("http://ornek.test", "/")
    assert _istek_hedefi("GET", "http://ornek.test/a/b") == ("http://ornek.test/a/b", "/a/b")


def test_tarayici_yerel_adrese_vekilsiz_ulasamaz(sahte_dns):
    """Uçtan uca: sayfa yerel adresteki bir kaynağı (görsel, fetch, yönlendirme) istese
    de tarayıcı vekili atlayamaz; yerel sunucuya hiçbir istek ulaşmaz."""
    pytest.importorskip("playwright")
    from yedek_okuyucu.sayfa_acici import EkranKurali, SayfaAcici

    async def calistir():
        async with _YerelSunucu() as gizli:
            sayfa_html = (
                "<html><head><title>Proje</title></head><body>"
                f"<img src='http://127.0.0.1:{gizli.port}/gizli.png'>"
                f"<img src='http://localhost:{gizli.port}/gizli2.png'>"
                f"<script>fetch('http://127.0.0.1:{gizli.port}/gizli3')</script>"
                "Bir çalışma sayfası.</body></html>"
            ).encode()
            sayfa_yaniti = (
                b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: "
                + str(len(sayfa_html)).encode()
                + b"\r\nConnection: close\r\n\r\n"
                + sayfa_html
            )
            async with _YerelSunucu(sayfa_yaniti) as acik:

                async def baglan(ip: str, port: int):
                    # Yalnızca denetimden geçen ornek.test buraya gelir.
                    assert ip == GENEL_IP
                    return await asyncio.open_connection("127.0.0.1", acik.port)

                vekil = SuzgecliVekil(baglan)
                await vekil.baslat()
                acici = SayfaAcici(vekil.port)
                try:
                    await acici.baslat()
                except Exception as hata:  # Chromium kurulu değil
                    await vekil.durdur()
                    pytest.skip(f"Chromium açılamadı: {hata}")
                try:
                    acilis = await acici.ac("http://ornek.test/", EkranKurali.HER_ZAMAN, 200)
                finally:
                    await acici.durdur()
                    await vekil.durdur()
                return acilis, gizli.gelenler

    acilis, gizliye_gelen = asyncio.run(calistir())
    assert acilis.hata is None and acilis.durum == 200
    assert "Bir çalışma sayfası." in acilis.html
    assert 1 <= len(acilis.ekran_goruntuleri) <= 3
    assert acilis.ekran_goruntuleri[0][:2] == b"\xff\xd8"  # JPEG
    assert gizliye_gelen == []
