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
    BREVO_ADRESI,
    BrevoGonderici,
    Eposta,
    KapaliGonderici,
    LogGonderici,
    ResendGonderici,
    SahteAdresiAtlayan,
    dusmeden_gonder,
    sahte_adres_mi,
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
        # Brevo: anahtar ya da gönderen eksikse yine log kipi, tamsa gerçek gönderici.
        ({"eposta_saglayici": "brevo", "eposta_gonderen": "a@ornek.org"}, LogGonderici),
        ({"eposta_saglayici": "brevo", "brevo_api_key": "xkeysib-x"}, LogGonderici),
        (
            {
                "eposta_saglayici": "brevo",
                "brevo_api_key": "xkeysib-x",
                "eposta_gonderen": "a@ornek.org",
            },
            BrevoGonderici,
        ),
    ],
)
def test_kurulum_bayraga_gore_secer(ayarlar, beklenen):
    ayar = Settings(
        _env_file=None,
        **{"resend_api_key": "", "brevo_api_key": "", "eposta_gonderen": "", **ayarlar},
    )
    gonderici = kurulum.eposta_gondericisi_sec(ayar)
    # Gerçek göndericiler sahte adres sarmalayıcısının içinde gelir; kip dışarıdan da görünür.
    ic = gonderici.ic if isinstance(gonderici, SahteAdresiAtlayan) else gonderici
    assert isinstance(ic, beklenen)
    assert gonderici.kip == ic.kip


def test_saglik_ucu_yalnizca_girvak():
    istemci = TestClient(app)
    assert istemci.get("/saglik/servisler").status_code == 401
    with giris_yapmis(sahte_hesap("genc")):
        assert istemci.get("/saglik/servisler").status_code == 403
    with giris_yapmis(sahte_hesap("girvak")):
        yanit = istemci.get("/saglik/servisler")
    assert yanit.status_code == 200
    assert [s["servis"] for s in yanit.json()] == [
        "eposta",
        "oauth",
        "depo",
        "virus",
        "yedek_okuyucu",
        "uzak_okuyucu",
        "gorsel_arayici",
    ]
    assert yanit.json()[0]["kip"] == "sahte"


# --- Brevo ve sahte adres koruması ---------------------------------------------------------


def _brevo(isleyici, gonderen="Zemin360 <bildirim@ornek.org>") -> BrevoGonderici:
    return BrevoGonderici(
        api_anahtari="brevo-test-anahtari",
        gonderen=gonderen,
        zaman_asimi_sn=5,
        tasima=httpx.MockTransport(isleyici),
    )


def test_brevo_istegi_ve_basari_kaydi(caplog):
    istekler = []

    def isleyici(istek):
        istekler.append(istek)
        return httpx.Response(201, json={"messageId": "<abc@smtp-relay>"})

    once = SAGLIK.oku("eposta").basari_sayisi
    eposta = Eposta(alici="elif@ornek.com", konu="Konu", metin="Metin", alici_adi="Elif")
    with caplog.at_level("INFO", logger="zemin360.eposta"):
        assert asyncio.run(dusmeden_gonder(_brevo(isleyici), eposta)) is True
    (istek,) = istekler
    assert istek.method == "POST" and str(istek.url) == BREVO_ADRESI
    assert istek.headers["api-key"] == "brevo-test-anahtari"
    assert istek.headers["content-type"] == "application/json"
    assert istek.headers["accept"] == "application/json"
    assert json.loads(istek.content) == {
        "sender": {"email": "bildirim@ornek.org", "name": "Zemin360"},
        "to": [{"email": "elif@ornek.com", "name": "Elif"}],
        "subject": "Konu",
        "textContent": "Metin",
    }
    assert SAGLIK.oku("eposta").basari_sayisi == once + 1
    # Başarıda log'a yalnızca messageId; anahtar ve alıcı yok.
    assert "messageId=<abc@smtp-relay>" in caplog.text
    assert "brevo-test-anahtari" not in caplog.text
    assert "elif@ornek.com" not in caplog.text


def test_brevo_alici_adi_yoksa_to_yalnizca_email():
    istekler = []
    gonderici = _brevo(lambda i: istekler.append(i) or httpx.Response(201, json={}))
    asyncio.run(gonderici.gonder(EPOSTA))
    assert json.loads(istekler[0].content)["to"] == [{"email": "elif@ornek.com"}]


def test_brevo_gonderen_yalnizca_adresse_ad_alani_yok():
    istekler = []
    gonderici = _brevo(
        lambda i: istekler.append(i) or httpx.Response(201, json={}), gonderen="a@ornek.org"
    )
    asyncio.run(gonderici.gonder(EPOSTA))
    assert json.loads(istekler[0].content)["sender"] == {"email": "a@ornek.org"}


def test_brevo_hatasi_mesaji_loglar_anahtari_ve_alici_adresini_yazmaz(caplog):
    once = SAGLIK.oku("eposta").hata_sayisi
    gonderici = _brevo(
        lambda _i: httpx.Response(
            400,
            json={
                "code": "invalid_parameter",
                "message": "elif@ornek.com is not valid; api-key brevo-test-anahtari rejected",
            },
        )
    )
    with caplog.at_level("INFO", logger="zemin360.eposta"):
        assert asyncio.run(dusmeden_gonder(gonderici, EPOSTA)) is False
    assert SAGLIK.oku("eposta").hata_sayisi == once + 1
    assert SAGLIK.oku("eposta").son_hata_turu == "BrevoHatasi"
    assert "durum=400" in caplog.text
    assert "[alici] is not valid" in caplog.text  # Brevo'nun mesajı görünür
    assert "brevo-test-anahtari" not in caplog.text
    assert "elif@ornek.com" not in caplog.text


def test_brevo_json_olmayan_hata_govdesi_de_guvenle_loglanir(caplog):
    gonderici = _brevo(lambda _i: httpx.Response(502, text="Bad gateway elif@ornek.com"))
    with caplog.at_level("INFO", logger="zemin360.eposta"):
        assert asyncio.run(dusmeden_gonder(gonderici, EPOSTA)) is False
    assert "Bad gateway [alici]" in caplog.text
    assert "elif@ornek.com" not in caplog.text


@pytest.mark.parametrize(
    ("adres", "sahte"),
    [
        ("ayse@soguklojistik.example", True),
        ("iletisim@demo.zemin360.example", True),
        ("x@deneme.test", True),
        ("x@yerel.localhost", True),
        ("x@gecersiz.invalid", True),
        ("x@example.com", True),
        ("X@EXAMPLE.ORG", True),
        ("elif@ornek.com", False),
        ("elif@gmail.com", False),
        # "example" yalnızca son parça olarak sahte; başka alan adının içinde geçmesi sahte değil.
        ("x@examplesirket.com", False),
        ("x@my.example.com", False),
    ],
)
def test_sahte_adres_mi(adres, sahte):
    assert sahte_adres_mi(adres) is sahte


def test_sahte_adrese_ag_istegi_atilmaz_gercek_adrese_atilir():
    istekler = []

    def isleyici(istek):
        istekler.append(istek)
        return httpx.Response(201)

    gonderici = SahteAdresiAtlayan(_brevo(isleyici))
    assert gonderici.kip == "brevo"

    sahte = Eposta(alici="ayse@soguklojistik.example", konu="K", metin="M")
    assert asyncio.run(dusmeden_gonder(gonderici, sahte)) is True  # hata değil, atlandı
    assert istekler == []

    assert asyncio.run(dusmeden_gonder(gonderici, EPOSTA)) is True
    assert len(istekler) == 1
