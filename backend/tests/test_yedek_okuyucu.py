"""Yedek okuyucu (plan § 5.1, § 5.5): zincirdeki kuralları, ekran görüntüsü okunuşu,
servis adaptörü, profil kodu okuması ve üçüncü taraf okuma (Jina, bayrakla). Ağ yok:
sayfalar MockTransport'tan, yedek okuyucu sahte.
"""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import json

import httpx
import pytest

from app.agents.dogrulama import okuma
from app.agents.dogrulama.dosya_cikarimi import DosyaOkunusu
from app.core import guvenli_istek
from app.core.dis_servisler.uzak_okuyucu import JinaOkuyucu, UzakSayfa
from app.core.dis_servisler.yedek_okuyucu import (
    EkranKurali,
    PlaywrightYedekOkuyucu,
    TarayiciSayfasi,
)
from app.core.kanit_okuma import kaniti_oku
from app.core.kanit_okuma.belge import ErisimDurumu as E
from app.core.kanit_okuma.belge import HesapIzi, KanitBelgesi
from app.core.kanit_okuma.onbellek import ZamanliOnbellek
from app.core.kanit_okuma.yedek import birlestir, ekran_kurali, yedek_gerekli_mi
from app.core.profil_kodu import sayfayi_oku

GOVDE = "Kampüs için ödünç takip sistemi; React ve FastAPI ile yazıldı. " * 10
ACIK_HTML = f"<html><head><title>Ödünç Takip</title></head><body><p>{GOVDE}</p></body></html>"
BOS_HTML = "<html><head><title>Shot</title></head><body><div id='app'></div></body></html>"
ENGEL_HTML = "<html><head><title>Just a moment...</title></head><body></body></html>"
JPEG = b"\xff\xd8\xff\xe0sahte"


@pytest.fixture(autouse=True)
def genel_ip(monkeypatch):
    async def coz(host, port):
        return [ipaddress.ip_address("93.184.216.34")]

    monkeypatch.setattr(guvenli_istek, "cozumleyici", coz)


class SahteYedek:
    kip = "sahte"

    def __init__(self, sayfa: TarayiciSayfasi | None) -> None:
        self.sayfa = sayfa
        self.istekler: list[tuple[str, EkranKurali, int]] = []

    async def ac(self, url, *, ekran, en_az_metin):
        self.istekler.append((url, ekran, en_az_metin))
        return self.sayfa


def sayfa(html: str, durum: int = 200, ekran: tuple[bytes, ...] = ()) -> TarayiciSayfasi:
    return TarayiciSayfasi(durum=durum, son_url="https://x", html=html, ekran_goruntuleri=ekran)


def belge(erisim: E, platform: str = "web", **alanlar) -> KanitBelgesi:
    return KanitBelgesi(url="https://x", erisim=erisim, platform=platform, **alanlar)


def u(adres: str) -> httpx.URL:
    return httpx.URL(adres)


# --- Saf kurallar --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("adres", "erisim", "platform", "beklenen"),
    [
        ("https://ornek.org/p", E.ENGELLENDI, "web", True),
        ("https://ornek.org/p", E.ICERIK_YOK, "web", True),
        # Tarayıcı giriş duvarını aşamaz; "yok" ve "güvensiz" kesin sonuçtur.
        ("https://ornek.org/p", E.GIRIS_GEREKLI, "web", False),
        ("https://ornek.org/p", E.BULUNAMADI, "web", False),
        ("https://ornek.org/p", E.GUVENSIZ, "web", False),
        ("https://ornek.org/p", E.HATA, "web", False),
        ("https://ornek.org/p", E.ACIK, "web", False),
        # PDF dosya hattının işi
        ("https://ornek.org/cv.pdf", E.ICERIK_YOK, "pdf", False),
        # Görsel platformda açık okunsa da ekran görüntüsü için
        ("https://dribbble.com/shots/1-x", E.ACIK, "web", True),
        ("https://ayse.myportfolio.com/proje", E.ACIK, "web", True),
        ("https://www.behance.net/gallery/1/x", E.GIRIS_GEREKLI, "web", False),
    ],
)
def test_yedek_gerekli_mi(adres, erisim, platform, beklenen):
    assert yedek_gerekli_mi(u(adres), belge(erisim, platform)) is beklenen


def test_ekran_kurali_gorsel_platformda_her_zaman():
    assert ekran_kurali(u("https://www.behance.net/gallery/1/x")) is EkranKurali.HER_ZAMAN
    assert ekran_kurali(u("https://cdn.dribbble.com/x")) is EkranKurali.HER_ZAMAN
    assert ekran_kurali(u("https://notdribbble.com/x")) is EkranKurali.METIN_AZSA
    assert ekran_kurali(u("https://www.kaggle.com/code/x")) is EkranKurali.METIN_AZSA


def test_birlestir_engelli_sayfa_tarayicida_acilir():
    sonuc = birlestir("https://x", belge(E.ENGELLENDI), sayfa(ACIK_HTML))
    assert sonuc.erisim is E.ACIK and "ödünç takip" in sonuc.metin.lower()


def test_birlestir_tarayici_da_engele_takilirsa_onceki_kalir():
    onceki = belge(E.ENGELLENDI)
    # Doğrulama sayfasının görüntüsü kanıt değildir.
    assert birlestir("https://x", onceki, sayfa(ENGEL_HTML, 403, (JPEG,))) is onceki


def test_birlestir_bos_sayfa_goruntuyle_gelir():
    sonuc = birlestir("https://x", belge(E.ENGELLENDI), sayfa(BOS_HTML, ekran=(JPEG,)))
    assert sonuc.erisim is E.ICERIK_YOK and sonuc.ekran_goruntuleri == (JPEG,)


def test_birlestir_bos_ve_goruntusuz_ise_onceki_kalir():
    onceki = belge(E.ICERIK_YOK)
    assert birlestir("https://x", onceki, sayfa(BOS_HTML)) is onceki


def test_birlestir_acik_okunusta_platform_verisi_korunur():
    iz = HesapIzi("dribbble", "ayse")
    onceki = belge(E.ACIK, metin="eski", hesaplar=(iz,), platform_metni="Beğeni: 3")
    sonuc = birlestir("https://x", onceki, sayfa(ACIK_HTML, ekran=(JPEG, JPEG)))
    assert sonuc.erisim is E.ACIK and "Ödünç" in sonuc.metin
    assert sonuc.hesaplar == (iz,) and sonuc.platform_metni == "Beğeni: 3"
    assert len(sonuc.ekran_goruntuleri) == 2


def test_birlestir_tarayici_bos_ama_onceki_acikti():
    onceki = belge(E.ACIK, metin="önceki metin")
    sonuc = birlestir("https://x", onceki, sayfa(BOS_HTML, ekran=(JPEG,)))
    assert sonuc.metin == "önceki metin" and sonuc.ekran_goruntuleri == (JPEG,)


# --- Zincir --------------------------------------------------------------------------------


def _engel_transport() -> httpx.MockTransport:
    return httpx.MockTransport(
        lambda istek: httpx.Response(403, headers={"content-type": "text/html"}, text=ENGEL_HTML)
    )


def test_zincir_engelde_yedege_gider_ve_esigi_iletir():
    yedek = SahteYedek(sayfa(ACIK_HTML))
    sonuc = asyncio.run(
        kaniti_oku("https://ornek.org/proje", transport=_engel_transport(), yedek=yedek)
    )
    assert sonuc.erisim is E.ACIK
    assert yedek.istekler == [("https://ornek.org/proje", EkranKurali.METIN_AZSA, 200)]


def test_zincir_yedek_yoksa_ya_da_acamazsa_onceki_durum():
    for yedek in (None, SahteYedek(None)):
        sonuc = asyncio.run(
            kaniti_oku("https://ornek.org/proje", transport=_engel_transport(), yedek=yedek)
        )
        assert sonuc.erisim is E.ENGELLENDI


# --- Ekran görüntüsünün okunuşu (değerlendirme katmanı) ------------------------------------


class SahteEkranOkuyucu:
    def __init__(self, okunus: DosyaOkunusu | Exception) -> None:
        self.okunus = okunus
        self.cagri = 0

    async def __call__(self, goruntuler):
        self.cagri += 1
        assert goruntuler == (JPEG,)
        if isinstance(self.okunus, Exception):
            raise self.okunus
        return self.okunus


async def _gom(metinler, tur):
    return [[1.0, 0.0] for _ in metinler]


def _kanit_oku(ekran_oku, adres="https://dribbble.com/shots/1-ui"):
    yedek = SahteYedek(sayfa(BOS_HTML, ekran=(JPEG,)))
    transport = httpx.MockTransport(
        lambda istek: httpx.Response(200, headers={"content-type": "text/html"}, text=BOS_HTML)
    )
    return asyncio.run(
        okuma.kanit_oku(
            adres,
            ["mobil uygulama"],
            transport=transport,
            gom=_gom,
            yedek=yedek,
            ekran_oku=ekran_oku,
        )
    )


def test_ekran_goruntusu_okunur_alinti_yalnizca_yazili_metinden():
    oku = SahteEkranOkuyucu(
        DosyaOkunusu(gorsel_metni="Bankacılık uygulaması · Giriş ekranı", betim="Mobil arayüz")
    )
    okunan = _kanit_oku(oku)
    assert okunan.erisim is E.ACIK
    assert okunan.metin.startswith("[Görülen: Mobil arayüz]")
    assert "Giriş ekranı" in okunan.metin
    # Betim modelin yazdığıdır; alıntı kaynağı değildir (§ 4.3).
    assert "Mobil arayüz" not in okunan.alinti_metni
    assert "Giriş ekranı" in okunan.alinti_metni
    # Kaynak herkese açık bir link: seviye C (yüklenen görsel gibi D değil).
    assert okunan.seviye.value == "kamuya_acik"


def test_ekran_okunusu_adres_basina_saklanir():
    oku = SahteEkranOkuyucu(DosyaOkunusu(gorsel_metni="", betim="Bir arayüz tasarımı"))
    _kanit_oku(oku)
    _kanit_oku(oku)
    assert oku.cagri == 1


def test_ekran_okunamazsa_icerik_yok_kalir():
    okunan = _kanit_oku(SahteEkranOkuyucu(RuntimeError("model yok")))
    assert okunan.erisim is E.ICERIK_YOK and okunan.metin == ""


def test_zamanli_onbellek_suresi_ve_kapasitesi():
    saat = [0.0]
    onbellek: ZamanliOnbellek[int] = ZamanliOnbellek(sure_sn=10, kapasite=2, saat=lambda: saat[0])
    onbellek.koy("a", 1)
    onbellek.koy("b", 2)
    onbellek.koy("c", 3)
    assert onbellek.al("a") is None and onbellek.al("c") == 3
    saat[0] = 11
    assert onbellek.al("c") is None


# --- Servis adaptörü -----------------------------------------------------------------------


def _adaptor(isleyici, anahtar="gizli") -> PlaywrightYedekOkuyucu:
    return PlaywrightYedekOkuyucu(
        "http://yedek.internal:8100/", anahtar, 5, transport=httpx.MockTransport(isleyici)
    )


def test_adaptor_istegi_ve_yaniti():
    gelen: list[httpx.Request] = []

    def isleyici(istek: httpx.Request) -> httpx.Response:
        gelen.append(istek)
        return httpx.Response(
            200,
            json={
                "durum": 200,
                "son_url": "https://dribbble.com/shots/1",
                "html": ACIK_HTML,
                "ekran_goruntuleri": [base64.b64encode(JPEG).decode()],
                "hata": None,
            },
        )

    sonuc = asyncio.run(
        _adaptor(isleyici).ac(
            "https://dribbble.com/shots/1", ekran=EkranKurali.HER_ZAMAN, en_az_metin=200
        )
    )
    assert sonuc == TarayiciSayfasi(200, "https://dribbble.com/shots/1", ACIK_HTML, (JPEG,))
    istek = gelen[0]
    assert str(istek.url) == "http://yedek.internal:8100/oku"
    assert istek.headers["authorization"] == "Bearer gizli"
    assert json.loads(istek.content) == {
        "url": "https://dribbble.com/shots/1",
        "ekran": "her_zaman",
        "en_az_metin": 200,
    }


@pytest.mark.parametrize(
    "yanit",
    [
        httpx.Response(200, json={"durum": None, "hata": "zaman_asimi"}),
        httpx.Response(200, json={"durum": None, "hata": "guvensiz"}),
        httpx.Response(401),
        httpx.Response(500),
    ],
)
def test_adaptor_acamazsa_none(yanit):
    sonuc = asyncio.run(
        _adaptor(lambda istek: yanit).ac("https://x", ekran=EkranKurali.HAYIR, en_az_metin=0)
    )
    assert sonuc is None


def test_adaptor_servis_ulasilamazsa_none():
    def isleyici(istek):
        raise httpx.ConnectError("bağlantı reddedildi", request=istek)

    sonuc = asyncio.run(_adaptor(isleyici).ac("https://x", ekran=EkranKurali.HAYIR, en_az_metin=0))
    assert sonuc is None


# --- Profil kodu ---------------------------------------------------------------------------


def test_profil_engelliyse_tarayicida_okunur():
    kod = "z360-abcd1234"
    yedek = SahteYedek(sayfa(f"<html><head><title>Elif</title></head><body>{kod}</body></html>"))
    okuma_ = asyncio.run(sayfayi_oku("https://dribbble.com/elif", _engel_transport(), yedek))
    assert okuma_.erisim is E.ICERIK_YOK and kod in okuma_.metin
    # Profilde ekran görüntüsü gerekmez.
    assert yedek.istekler == [("https://dribbble.com/elif", EkranKurali.HAYIR, 0)]


def test_profil_tarayici_da_acamazsa_engel_kalir():
    okuma_ = asyncio.run(
        sayfayi_oku("https://dribbble.com/elif", _engel_transport(), SahteYedek(None))
    )
    assert okuma_.erisim is E.ENGELLENDI


# --- Üçüncü taraf okuma (Jina) ---------------------------------------------------------


class SahteUzak:
    kip = "sahte"

    def __init__(self, sayfa: UzakSayfa | None) -> None:
        self.sayfa = sayfa
        self.istekler: list[str] = []

    async def oku(self, url):
        self.istekler.append(url)
        return self.sayfa


def _engelli_oku(yedek, uzak):
    return asyncio.run(
        kaniti_oku("https://ornek.org/proje", transport=_engel_transport(), yedek=yedek, uzak=uzak)
    )


def test_tarayici_okuyamazsa_uzak_okuyucu_denenir():
    uzak = SahteUzak(UzakSayfa("Ödünç Takip", GOVDE, "https://ornek.org/proje"))
    sonuc = _engelli_oku(SahteYedek(None), uzak)
    assert sonuc.erisim is E.ACIK and sonuc.metin.startswith("Başlık: Ödünç Takip")
    assert uzak.istekler == ["https://ornek.org/proje"]


def test_uzak_okuyucu_de_engele_takilirsa_onceki_kalir():
    uzak = SahteUzak(UzakSayfa("Just a moment...", "Bekleyin", "https://ornek.org/proje"))
    assert _engelli_oku(SahteYedek(sayfa(ENGEL_HTML, 403)), uzak).erisim is E.ENGELLENDI


def test_tarayici_okuduysa_uzak_okuyucu_cagrilmaz():
    uzak = SahteUzak(UzakSayfa("x", GOVDE, "https://x"))
    assert _engelli_oku(SahteYedek(sayfa(ACIK_HTML)), uzak).erisim is E.ACIK
    # Görüntü de okunmuş sayılır (model okuyacak).
    _engelli_oku(SahteYedek(sayfa(BOS_HTML, ekran=(JPEG,))), uzak)
    assert uzak.istekler == []


def _jina(isleyici, anahtar="j-anahtar") -> JinaOkuyucu:
    return JinaOkuyucu(anahtar, 5, transport=httpx.MockTransport(isleyici))


def test_jina_istegi_ve_yaniti():
    gelen: list[httpx.Request] = []

    def isleyici(istek: httpx.Request) -> httpx.Response:
        gelen.append(istek)
        veri = {"title": "Proje", "url": "https://ornek.org/proje", "content": GOVDE}
        return httpx.Response(200, json={"code": 200, "data": veri})

    sonuc = asyncio.run(_jina(isleyici).oku("https://ornek.org/proje"))
    assert sonuc == UzakSayfa("Proje", GOVDE.strip(), "https://ornek.org/proje")
    istek = gelen[0]
    # Sabit API ucu da güvenli istek katmanından (IP'ye sabitlenmiş, Host özgün ad).
    assert istek.headers["host"] == "r.jina.ai"
    assert istek.url.raw_path == b"/https://ornek.org/proje"
    assert istek.headers["authorization"] == "Bearer j-anahtar"


@pytest.mark.parametrize(
    "yanit",
    [
        httpx.Response(422, json={"code": 422, "data": None}),
        httpx.Response(200, json={"code": 200, "data": {"title": "x", "content": "  "}}),
        httpx.Response(200, text="json değil"),
    ],
)
def test_jina_okuyamazsa_none(yanit):
    assert asyncio.run(_jina(lambda istek: yanit).oku("https://x.org")) is None
