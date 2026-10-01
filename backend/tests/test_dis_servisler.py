"""Dış servis katmanı (plan § 14.4): Resend adaptörü, zarif düşüş, sarmalayıcılar,
kurulum bayrakları ve GİRVAK'a açık sağlık ucu."""

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.dis_servisler import kurulum
from app.core.dis_servisler.eposta import (
    Eposta,
    KapaliGonderici,
    LogGonderici,
    ResendGonderici,
    dusmeden_gonder,
)
from app.core.dis_servisler.saglik import SAGLIK
from app.core.dis_servisler.sarmalayicilar import zaman_asimli
from app.main import app
from tests.sahte_hesap import giris_yapmis, sahte_hesap

EPOSTA = Eposta(alici="elif@ornek.com", konu="Konu", metin="Metin")


def _resend(isleyici) -> ResendGonderici:
    return ResendGonderici(
        api_anahtari="re_test",
        gonderen="Zemin360 <bildirim@ornek.org>",
        zaman_asimi_sn=5,
        tasima=httpx.MockTransport(isleyici),
    )


def test_resend_istegi_ve_basari_kaydi():
    istekler = []

    def isleyici(istek):
        istekler.append(istek)
        return httpx.Response(200, json={"id": "x"})

    once = SAGLIK.oku("eposta").basari_sayisi
    assert asyncio.run(dusmeden_gonder(_resend(isleyici), EPOSTA)) is True
    (istek,) = istekler
    assert istek.headers["Authorization"] == "Bearer re_test"
    assert json.loads(istek.content) == {
        "from": "Zemin360 <bildirim@ornek.org>",
        "to": ["elif@ornek.com"],
        "subject": "Konu",
        "text": "Metin",
    }
    assert SAGLIK.oku("eposta").basari_sayisi == once + 1


def test_resend_hatasi_akisi_dusurmez_ve_saglikta_gorunur():
    once = SAGLIK.oku("eposta").hata_sayisi
    gonderici = _resend(lambda _i: httpx.Response(500))
    assert asyncio.run(dusmeden_gonder(gonderici, EPOSTA)) is False
    kayit = SAGLIK.oku("eposta")
    assert kayit.hata_sayisi == once + 1
    assert kayit.son_hata_turu == "HTTPStatusError"


def test_zaman_asimli_sureyi_asarsa_timeout():
    @zaman_asimli(lambda: 0.01)
    async def yavas():
        await asyncio.sleep(1)

    with pytest.raises(TimeoutError):
        asyncio.run(yavas())


@pytest.mark.parametrize(
    ("ayarlar", "beklenen"),
    [
        ({"eposta_saglayici": "kapali"}, KapaliGonderici),
        ({"eposta_saglayici": "log"}, LogGonderici),
        # Anahtar ya da gönderen eksikse açılış durmaz, log kipine düşer.
        ({"eposta_saglayici": "resend", "eposta_gonderen": "a@ornek.org"}, LogGonderici),
        ({"eposta_saglayici": "resend", "resend_api_key": "re_x"}, LogGonderici),
        (
            {
                "eposta_saglayici": "resend",
                "resend_api_key": "re_x",
                "eposta_gonderen": "a@ornek.org",
            },
            ResendGonderici,
        ),
    ],
)
def test_kurulum_bayraga_gore_secer(ayarlar, beklenen):
    ayar = Settings(_env_file=None, **{"resend_api_key": "", "eposta_gonderen": "", **ayarlar})
    assert isinstance(kurulum.eposta_gondericisi_sec(ayar), beklenen)


def test_saglik_ucu_yalnizca_girvak():
    istemci = TestClient(app)
    assert istemci.get("/saglik/servisler").status_code == 401
    with giris_yapmis(sahte_hesap("genc")):
        assert istemci.get("/saglik/servisler").status_code == 403
    with giris_yapmis(sahte_hesap("girvak")):
        yanit = istemci.get("/saglik/servisler")
    assert yanit.status_code == 200
    assert [s["servis"] for s in yanit.json()] == ["eposta"]
    assert yanit.json()[0]["kip"] == "sahte"
