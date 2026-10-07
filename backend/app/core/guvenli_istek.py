"""Kullanıcının verdiği adrese sunucudan güvenli istek (SSRF engeli).

Doğrulama, kanıt linkinin başlığını okumak için kullanıcının yazdığı adrese
sunucudan istek atıyor. Denetimsiz bırakılırsa bu, sunucunun kendi iç ağına
açılan bir kapı olur: `http://localhost:…`, bulut sağlayıcısının kimlik
bilgisi servisi (`169.254.169.254`), `10.x` / `192.168.x` gibi iç adresler.

Kurallar (hepsi her yönlendirme adımında yeniden uygulanır):
  - Yalnızca `http` ve `https`; yalnızca 80 ve 443 portları.
  - Adreste kullanıcı adı/şifre (`kullanici:sifre@`) yok.
  - Alan adının çözüldüğü **bütün** IP'ler genel internette olmalı
    (`ipaddress.is_global`): loopback, özel ağ, link-local, paylaşılan adres
    alanı (100.64/10), çok noktaya yayın, ayrılmış ve belirsiz adresler ret.
    IPv4'e eşlenmiş IPv6 (`::ffff:127.0.0.1`) IPv4 karşılığıyla denetlenir.
  - Yönlendirmeler otomatik izlenmez; en çok `EN_COK_YONLENDIRME` adım, her
    adımın hedefi baştan denetlenir.
  - DNS yeniden bağlama (denetimden sonra adres değişmesi) kapalı: bağlantı
    denetlenen IP'ye kurulur; `Host` başlığı ve TLS'teki sunucu adı (SNI)
    özgün alan adıdır, sertifika da ona göre doğrulanır.

Saf denetim (`ip_guvenli_mi`) ve çözümleyici ayrı: testler çözümleyiciyi
değiştirir, ağa çıkmaz.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx

IZINLI_SEMALAR = frozenset({"http", "https"})
IZINLI_PORTLAR = frozenset({80, 443})
EN_COK_YONLENDIRME = 5

IpAdresi = ipaddress.IPv4Address | ipaddress.IPv6Address


class GuvensizAdres(Exception):
    """Adres güvenli değil; istek atılmadı. Mesaj log içindir."""


class AdresBulunamadi(GuvensizAdres):
    """Alan adı çözülemedi: sayfa yok (güvenlik sorunu değil).

    `GuvensizAdres`'in alt sınıfı: istek yine atılmaz, ama okuyucu "adres
    bulunamadı" der, "güvensiz" değil.
    """


def ip_guvenli_mi(ip: IpAdresi) -> bool:
    """Genel internette, tek noktaya yayın bir adres mi?"""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


async def _sistem_cozumleyicisi(host: str, port: int) -> list[IpAdresi]:
    kayitlar = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    # IPv6 kapsam kimliği ("fe80::1%eth0") ip_address'e verilemez; kapsamlı
    # adres zaten link-local, düşürülünce de güvensiz sayılır.
    return [ipaddress.ip_address(kayit[4][0].split("%")[0]) for kayit in kayitlar]


# Testler bunu değiştirir (ağa çıkmadan).
cozumleyici: Callable[[str, int], Awaitable[list[IpAdresi]]] = _sistem_cozumleyicisi


@dataclass(frozen=True)
class Hedef:
    url: httpx.URL
    host: str
    ip: IpAdresi


async def hedefi_dogrula(adres: str | httpx.URL) -> Hedef:
    """Adres kurallara uyuyorsa bağlanılacak IP'yle döner; uymuyorsa `GuvensizAdres`."""
    try:
        url = httpx.URL(adres)
    except (httpx.InvalidURL, TypeError, ValueError) as hata:
        raise GuvensizAdres("adres okunamadı") from hata
    if url.scheme not in IZINLI_SEMALAR:
        raise GuvensizAdres(f"desteklenmeyen şema: {url.scheme or '(yok)'}")
    if url.userinfo:
        raise GuvensizAdres("adreste kullanıcı bilgisi var")
    host = url.host
    if not host:
        raise GuvensizAdres("alan adı yok")
    port = url.port or (443 if url.scheme == "https" else 80)
    if port not in IZINLI_PORTLAR:
        raise GuvensizAdres(f"izin verilmeyen port: {port}")

    try:
        ipler: list[IpAdresi] = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            ipler = await cozumleyici(host, port)
        except (OSError, UnicodeError) as hata:
            raise AdresBulunamadi("alan adı çözümlenemedi") from hata
    if not ipler:
        raise AdresBulunamadi("alan adı çözümlenemedi")
    # Biri bile iç ağdaysa ret: çözümleyici her seferinde farklı sırayla dönebilir.
    guvensiz = [ip for ip in ipler if not ip_guvenli_mi(ip)]
    if guvensiz:
        raise GuvensizAdres(f"iç ağ ya da ayrılmış adres: {guvensiz[0]}")
    return Hedef(url=url, host=host, ip=ipler[0])


def _sabitlenmis_istek(
    istemci: httpx.AsyncClient, hedef: Hedef, basliklar: Mapping[str, str] | None = None
) -> httpx.Request:
    """Bağlantı denetlenen IP'ye; `Host` ve SNI özgün alan adı (yeniden bağlama kapalı)."""
    url = hedef.url.copy_with(host=str(hedef.ip))
    host_basligi = hedef.url.netloc.decode("ascii")
    uzantilar = {"sni_hostname": hedef.host} if hedef.url.scheme == "https" else {}
    return istemci.build_request(
        "GET", url, headers={**(basliklar or {}), "Host": host_basligi}, extensions=uzantilar
    )


@asynccontextmanager
async def guvenli_get(
    adres: str,
    *,
    zaman_asimi: float,
    transport: httpx.AsyncBaseTransport | None = None,
    basliklar: Mapping[str, str] | None = None,
) -> AsyncIterator[httpx.Response]:
    """Kurallara uyan adrese akışlı GET; yönlendirmeleri kendisi ve denetleyerek izler.

    `GuvensizAdres` (adres ya da bir yönlendirme hedefi kurala uymuyor) ve
    `httpx.HTTPError` (ağ hatası, çok fazla yönlendirme) çağırana çıkar.
    """
    async with httpx.AsyncClient(
        timeout=zaman_asimi, follow_redirects=False, transport=transport
    ) as istemci:
        simdiki: httpx.URL = httpx.URL(adres)
        for _ in range(EN_COK_YONLENDIRME + 1):
            hedef = await hedefi_dogrula(simdiki)
            yanit = await istemci.send(_sabitlenmis_istek(istemci, hedef, basliklar), stream=True)
            konum = yanit.headers.get("location") if yanit.is_redirect else None
            if konum is None:
                # Yönlendirmelerden sonraki özgün adres (bağlantı IP'ye kurulduğu için
                # `yanit.url` IP'li): giriş duvarına yönlenme bununla anlaşılır.
                yanit.extensions["ozgun_url"] = str(hedef.url)
                try:
                    yield yanit
                finally:
                    await yanit.aclose()
                return
            await yanit.aclose()
            # Göreli yönlendirme özgün (sabitlenmemiş) adrese göre çözülür.
            simdiki = hedef.url.join(konum)
        raise httpx.TooManyRedirects("Çok fazla yönlendirme", request=None)
