"""Doğrulama koduyla hesap bağlama (docs/dogrulama.md § 6.2): kod,
platform stratejileri (adresi biz kurarız), profil okuma, uçlar ve GİRVAK'ın elle
doğrulaması.

Dünya: test_sahiplik.py — genc1 "Elif", kartı K1; genc2 "Can".
"""

import asyncio
import datetime as dt

import httpx
import pytest
from sqlalchemy import select, update

from app.core.dis_servisler import kurulum
from app.core.kanit_okuma.belge import ErisimDurumu
from app.core.profil_kodu import (
    KisiselSitePlatformu,
    ProfilOkumasi,
    SayfaPlatformu,
    YoutubePlatformu,
    kod_geciyor_mu,
    kod_uret,
    sayfayi_oku,
)
from app.models.bagli_hesap import BagliHesap, ProfilKodu
from app.models.bildirim import TUR_HESAP_BAGLAMA_SONUCU, Bildirim
from app.models.inceleme_isareti import TUR_PROFIL_KODU_ELLE, IncelemeIsareti
from tests.test_sahiplik import durumlar, senaryo

# --- Saf kurallar --------------------------------------------------------------------------


def test_kod_bicimi_ve_sozcuk_siniri():
    kod = kod_uret()
    assert kod.startswith("z360-") and len(kod) == 13
    assert kod_geciyor_mu(kod, f"Merhaba, ben Elif. {kod.upper()}")
    assert not kod_geciyor_mu(kod, f"{kod}x")
    assert not kod_geciyor_mu(kod, f"a-{kod}")


MEDIUM = SayfaPlatformu("medium", "https://medium.com/@{ad}")


@pytest.mark.parametrize(
    ("platform", "adres", "beklenen"),
    [
        # Sorgu dizesi atılır: kod başkasının sayfasında yankılanamaz.
        (
            MEDIUM,
            "https://medium.com/@Elif?x=z360-abc",
            ("Elif", "elif", "https://medium.com/@Elif"),
        ),
        (MEDIUM, "https://github.com/elif", None),
        (
            KisiselSitePlatformu(),
            "https://www.ayse.dev/hakkimda?x=1",
            ("ayse.dev", "ayse.dev", "https://ayse.dev/"),
        ),
        (KisiselSitePlatformu(), "https://medium.com/@ayse", None),
        (
            YoutubePlatformu(),
            "youtube.com/@Kanal/videos",
            ("Kanal", "kanal", "https://www.youtube.com/@Kanal"),
        ),
        (
            YoutubePlatformu(),
            "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
            (
                "UCuAXFkgsw1L7xaCfnd5JJOw",
                "UCuAXFkgsw1L7xaCfnd5JJOw",
                "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
            ),
        ),
    ],
)
def test_profil_adresini_platform_kurar(platform, adres, beklenen):
    profil = platform.profil(adres)
    assert ((profil.kullanici_adi, profil.dis_kimlik, profil.adres) if profil else None) == (
        beklenen
    )


def _tasima(yanitlar: dict[str, httpx.Response]) -> httpx.MockTransport:
    def isle(istek: httpx.Request) -> httpx.Response:
        anahtar = istek.headers["host"] + istek.url.path
        return yanitlar.get(anahtar, httpx.Response(404))

    return httpx.MockTransport(isle)


def test_kisa_profilde_kod_meta_aciklamasinda_bulunur():
    sayfa = (
        '<html><head><title>Elif</title><meta name="description" content="z360-abcd1234">'
        "</head></html>"
    )
    okuma = asyncio.run(
        sayfayi_oku(
            "https://medium.com/@elif",
            _tasima({"medium.com/@elif": httpx.Response(200, html=sayfa)}),
        )
    )
    assert kod_geciyor_mu("z360-abcd1234", okuma.metin)


def test_youtube_api_aciklama_ve_kanal_no():
    profil = YoutubePlatformu().profil("youtube.com/@Kanal")
    tasima = _tasima(
        {
            "www.googleapis.com/youtube/v3/channels": httpx.Response(
                200,
                json={"items": [{"id": "UC1", "snippet": {"title": "K", "description": "z360-x"}}]},
            )
        }
    )
    okuma = asyncio.run(YoutubePlatformu("anahtar").oku(profil, tasima))
    assert (okuma.erisim, okuma.dis_kimlik, "z360-x" in okuma.metin) == (
        ErisimDurumu.ACIK,
        "UC1",
        True,
    )
    bos = _tasima({"www.googleapis.com/youtube/v3/channels": httpx.Response(200, json={})})
    assert asyncio.run(YoutubePlatformu("anahtar").oku(profil, bos)).erisim is (
        ErisimDurumu.BULUNAMADI
    )


# --- Uçlar ---------------------------------------------------------------------------------


class SahtePlatform:
    """Profil adresi kuralı gerçek (Medium), okuma sahte."""

    platform = "medium"

    def __init__(self) -> None:
        self.okuma = ProfilOkumasi(ErisimDurumu.ACIK, "Profil açıklaması")

    def profil(self, adres):
        return MEDIUM.profil(adres)

    async def oku(self, profil, transport=None):
        return self.okuma


@pytest.fixture
def medium(monkeypatch):
    sahte = SahtePlatform()
    monkeypatch.setattr(kurulum, "profil_kodu_platformlari", lambda: {"medium": sahte})
    return sahte


async def _kod_al(istemci, kisi, adres="https://medium.com/@elif?ref=x"):
    yanit = await istemci.post(
        "/hesap-baglama/profil-kodu",
        headers=kisi.baslik,
        json={"platform": "medium", "profil_adresi": adres},
    )
    assert yanit.status_code == 201, yanit.text
    return yanit.json()


async def _dogrula(istemci, kisi):
    return await istemci.post("/hesap-baglama/profil-kodu/medium/dogrula", headers=kisi.baslik)


def test_kod_profilde_bulununca_baglanir(medium, kalemleri_yeniden_okuma_arka_plani_yok):
    async def adimlar(istemci, d):
        kod = await _kod_al(istemci, d.genc1)
        assert kod["profil_adresi"] == "https://medium.com/@elif"
        liste = (await istemci.get("/hesap-baglama", headers=d.genc1.baslik)).json()
        assert [k["kod"] for k in liste["bekleyen_kodlar"]] == [kod["kod"]]

        assert (await _dogrula(istemci, d.genc1)).status_code == 422  # kod henüz yok
        medium.okuma = ProfilOkumasi(ErisimDurumu.ACIK, f"Tasarımcı. {kod['kod']}")
        yanit = await _dogrula(istemci, d.genc1)
        assert yanit.status_code == 201
        assert yanit.json()["durum"] == "baglandi"
        assert (yanit.json()["hesap"]["kullanici_adi"], yanit.json()["hesap"]["yontem"]) == (
            "elif",
            "profil_kodu",
        )
        assert kalemleri_yeniden_okuma_arka_plani_yok == [d.K1.id]
        liste = (await istemci.get("/hesap-baglama", headers=d.genc1.baslik)).json()
        assert liste["bekleyen_kodlar"] == []
        # Kod bağlandıktan sonra silinir; ikinci doğrulama "kod yok".
        assert (await _dogrula(istemci, d.genc1)).status_code == 404

    senaryo(adimlar)


def test_okunamayan_profil_girvak_elle_dogrular(medium, kalemleri_yeniden_okuma_arka_plani_yok):
    async def adimlar(istemci, d):
        await _kod_al(istemci, d.genc1)
        medium.okuma = ProfilOkumasi(ErisimDurumu.ENGELLENDI)
        yanit = await _dogrula(istemci, d.genc1)
        assert (yanit.status_code, yanit.json()["durum"]) == (202, "inceleme_bekliyor")
        # Yeniden denemek ikinci işaret açmaz.
        assert (await _dogrula(istemci, d.genc1)).status_code == 202
        liste = (await istemci.get("/hesap-baglama", headers=d.genc1.baslik)).json()
        assert liste["inceleme_bekleyen"] == "medium"

        isaret = await d.oturum.scalar(
            select(IncelemeIsareti).where(
                IncelemeIsareti.tur == TUR_PROFIL_KODU_ELLE,
                IncelemeIsareti.kullanici_id == d.genc1.profil.id,
            )
        )
        assert isaret.ayrinti["profil_adresi"] == "https://medium.com/@elif"
        yanit = await istemci.post(
            f"/girvak/inceleme/{isaret.id}/karar",
            headers=d.girvak.baslik,
            json={"karar": "kapandi"},
        )
        assert yanit.status_code == 200
        bagli = await d.oturum.scalar(
            select(BagliHesap).where(BagliHesap.kullanici_id == d.genc1.profil.id)
        )
        assert (bagli.saglayici, bagli.kullanici_adi, bagli.yontem) == ("medium", "elif", "elle")
        bildirim = await d.oturum.scalar(
            select(Bildirim).where(
                Bildirim.hesap_id == d.genc1.hesap.id, Bildirim.tur == TUR_HESAP_BAGLAMA_SONUCU
            )
        )
        assert "Medium hesabın doğrulandı" in bildirim.metin
        assert kalemleri_yeniden_okuma_arka_plani_yok == [d.K1.id]

    senaryo(adimlar)


def test_girvak_kodu_gormediyse_baglanmaz(medium):
    async def adimlar(istemci, d):
        await _kod_al(istemci, d.genc1)
        medium.okuma = ProfilOkumasi(ErisimDurumu.GIRIS_GEREKLI)
        await _dogrula(istemci, d.genc1)
        isaret = await d.oturum.scalar(
            select(IncelemeIsareti).where(IncelemeIsareti.kullanici_id == d.genc1.profil.id)
        )
        await istemci.post(
            f"/girvak/inceleme/{isaret.id}/karar",
            headers=d.girvak.baslik,
            json={"karar": "dogrulanamadi"},
        )
        sayi = await d.oturum.scalar(
            select(BagliHesap.id).where(BagliHesap.kullanici_id == d.genc1.profil.id)
        )
        assert sayi is None

    senaryo(adimlar)


def test_kod_hatalari(medium):
    async def adimlar(istemci, d):
        assert (await _dogrula(istemci, d.genc1)).status_code == 404  # kod alınmadı
        yanit = await istemci.post(
            "/hesap-baglama/profil-kodu",
            headers=d.genc1.baslik,
            json={"platform": "medium", "profil_adresi": "https://github.com/elif"},
        )
        assert yanit.status_code == 422
        yanit = await istemci.post(
            "/hesap-baglama/profil-kodu",
            headers=d.genc1.baslik,
            json={"platform": "linkedin", "profil_adresi": "https://linkedin.com/in/elif"},
        )
        assert yanit.status_code == 404

        await _kod_al(istemci, d.genc1)
        medium.okuma = ProfilOkumasi(ErisimDurumu.BULUNAMADI)
        assert (await _dogrula(istemci, d.genc1)).status_code == 422
        await d.oturum.execute(
            update(ProfilKodu)
            .where(ProfilKodu.kullanici_id == d.genc1.profil.id)
            .values(son_gecerlilik=dt.datetime.now(dt.UTC) - dt.timedelta(minutes=1))
        )
        assert (await _dogrula(istemci, d.genc1)).status_code == 409

    senaryo(adimlar)


def test_baskasina_bagli_profil_409(medium):
    async def adimlar(istemci, d):
        for kisi, beklenen in ((d.genc1, 201), (d.genc2, 409)):
            kod = await _kod_al(istemci, kisi)
            medium.okuma = ProfilOkumasi(ErisimDurumu.ACIK, kod["kod"])
            assert (await _dogrula(istemci, kisi)).status_code == beklenen

    senaryo(adimlar)


def test_yetki():
    async def adimlar(istemci, d):
        await durumlar(
            istemci,
            "POST",
            "/hesap-baglama/profil-kodu",
            {None: 401, d.kurum1: 403, d.girvak: 403},
            json={"platform": "medium", "profil_adresi": "https://medium.com/@elif"},
        )
        await durumlar(
            istemci,
            "POST",
            "/hesap-baglama/profil-kodu/medium/dogrula",
            {None: 401, d.kurum1: 403},
        )

    senaryo(adimlar)
