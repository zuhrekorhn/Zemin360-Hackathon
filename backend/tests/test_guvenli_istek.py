"""SSRF engeli: kanıt linki kontrolü iç ağa istek atmaz (app/core/guvenli_istek.py).

Ağa çıkılmaz: çözümleyici ve HTTP taşıyıcısı sahte.
"""

from __future__ import annotations

import asyncio
import ipaddress

import httpx
import pytest

from app.core import guvenli_istek
from app.core.guvenli_istek import (
    GuvensizAdres,
    guvenli_get,
    hedefi_dogrula,
    ip_guvenli_mi,
)
from app.core.kanit_okuma import kaniti_oku
from app.core.kanit_okuma.belge import ErisimDurumu

GENEL = "93.184.216.34"


@pytest.fixture(autouse=True)
def sahte_dns(monkeypatch):
    """Alan adı → IP listesi; listede olmayan ad çözümlenemez."""
    kayitlar = {
        "ornek.com": [GENEL],
        "baska.ornek.com": ["93.184.216.35"],
        "ic.ornek.com": ["10.0.0.5"],
        "localhost": ["127.0.0.1"],
        "karisik.ornek.com": [GENEL, "192.168.1.10"],
        "metadata.ornek.com": ["169.254.169.254"],
        "v6.ornek.com": ["::1"],
    }

    async def coz(host, port):
        if host not in kayitlar:
            raise OSError("çözümlenemedi")
        return [ipaddress.ip_address(ip) for ip in kayitlar[host]]

    monkeypatch.setattr(guvenli_istek, "cozumleyici", coz)


def _dogrula(adres):
    return asyncio.run(hedefi_dogrula(adres))


# --- Saf kurallar ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ip", "guvenli"),
    [
        (GENEL, True),
        ("2606:2800:220:1:248:1893:25c8:1946", True),
        ("127.0.0.1", False),
        ("10.1.2.3", False),
        ("172.16.0.1", False),
        ("192.168.0.1", False),
        ("169.254.169.254", False),  # bulut kimlik servisi
        ("100.64.0.1", False),  # paylaşılan adres alanı
        ("0.0.0.0", False),
        ("224.0.0.1", False),
        ("::1", False),
        ("fc00::1", False),
        ("fe80::1", False),
        ("::ffff:127.0.0.1", False),  # IPv4'e eşlenmiş loopback
        ("::ffff:93.184.216.34", True),
    ],
)
def test_ip_guvenli_mi(ip, guvenli):
    assert ip_guvenli_mi(ipaddress.ip_address(ip)) is guvenli


def test_genel_adres_gecer():
    hedef = _dogrula("https://ornek.com/proje")
    assert str(hedef.ip) == GENEL and hedef.host == "ornek.com"


@pytest.mark.parametrize(
    "adres",
    [
        "http://localhost/",
        "http://127.0.0.1/",
        "http://ic.ornek.com/",
        "http://karisik.ornek.com/",  # IP'lerden biri bile iç ağdaysa ret
        "http://metadata.ornek.com/latest/meta-data/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://v6.ornek.com/",
        "http://0.0.0.0/",
        "file:///etc/passwd",
        "gopher://ornek.com/",
        "ftp://ornek.com/",
        "http://ornek.com:22/",
        "http://ornek.com:8080/",
        "https://kullanici:sifre@ornek.com/",
        "http://bilinmeyen.ornek.com/",
        "http:///yol",
    ],
)
def test_guvensiz_adresler_reddedilir(adres):
    with pytest.raises(GuvensizAdres):
        _dogrula(adres)


# --- İstek: sabitleme ve yönlendirmeler ------------------------------------------------


def _getir(adres, isleyici):
    async def calistir():
        async with guvenli_get(
            adres, zaman_asimi=2, transport=httpx.MockTransport(isleyici)
        ) as yanit:
            await yanit.aread()
            return yanit

    return asyncio.run(calistir())


def test_istek_denetlenen_ipye_gider_host_ve_sni_alan_adi():
    gorulen = []

    def isleyici(istek: httpx.Request):
        gorulen.append(istek)
        return httpx.Response(200, text="<title>Proje</title>")

    yanit = _getir("https://ornek.com/proje?x=1", isleyici)
    assert yanit.status_code == 200
    istek = gorulen[0]
    assert istek.url.host == GENEL  # DNS yeniden bağlama kapalı
    assert istek.url.path == "/proje" and istek.url.query == b"x=1"
    assert istek.headers["host"] == "ornek.com"
    assert istek.extensions["sni_hostname"] == "ornek.com"


def test_ic_aga_yonlendirme_izlenmez():
    ic_aga_gidildi = []

    def isleyici(istek: httpx.Request):
        if istek.url.host == GENEL:
            return httpx.Response(302, headers={"location": "http://169.254.169.254/"})
        ic_aga_gidildi.append(istek)
        return httpx.Response(200)

    with pytest.raises(GuvensizAdres):
        _getir("https://ornek.com/", isleyici)
    assert ic_aga_gidildi == []


def test_goreli_ve_baska_genel_alana_yonlendirme_izlenir():
    def isleyici(istek: httpx.Request):
        if istek.headers["host"] == "ornek.com" and istek.url.path == "/":
            return httpx.Response(301, headers={"location": "/yeni"})
        if istek.headers["host"] == "ornek.com" and istek.url.path == "/yeni":
            return httpx.Response(302, headers={"location": "https://baska.ornek.com/son"})
        return httpx.Response(200, text="<title>Son</title>")

    yanit = _getir("https://ornek.com/", isleyici)
    assert yanit.status_code == 200
    assert yanit.request.headers["host"] == "baska.ornek.com"


def test_cok_fazla_yonlendirme():
    def isleyici(istek: httpx.Request):
        return httpx.Response(302, headers={"location": "/tekrar"})

    with pytest.raises(httpx.TooManyRedirects):
        _getir("https://ornek.com/", isleyici)


# --- Kanıt kontrolü ----------------------------------------------------------------------


def test_kanit_kontrolu_ic_ag_linkini_acilmiyor_sayar():
    def isleyici(istek: httpx.Request):
        raise AssertionError("iç ağa istek atıldı")

    belge = asyncio.run(
        kaniti_oku("http://localhost:8000/admin", transport=httpx.MockTransport(isleyici))
    )
    assert belge.erisim is ErisimDurumu.GUVENSIZ


def test_kanit_kontrolu_genel_linki_okur():
    def isleyici(istek: httpx.Request):
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<head><title>Kütüphane sistemi</title></head><body>" + "Ödünç takibi. " * 30,
        )

    belge = asyncio.run(kaniti_oku("ornek.com/proje", transport=httpx.MockTransport(isleyici)))
    assert belge.erisim is ErisimDurumu.ACIK
    assert "Kütüphane sistemi" in belge.metin
