"""Hesap bağlama (docs/plans/dogrulama-iyilestirme.md § 6.1): OAuth adaptörleri, kurulum,
uçlar (başlat → dönüş → tamamla), tekillik, sahiplik ve arka planda yeniden okuma.

Dünya: test_sahiplik.py — genc1 "Elif", kartı K1; genc2 "Can", kartı K2.
"""

import asyncio
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.dis_servisler.kurulum import oauth_saglayicilarini_sec
from app.core.dis_servisler.oauth import (
    DisHesap,
    GithubOAuth,
    GitlabOAuth,
    OAuthAyari,
    OAuthReddedildi,
    OrcidOAuth,
)
from app.models.bagli_hesap import BagliHesap
from tests.test_sahiplik import durumlar, senaryo

# --- Adaptörler ----------------------------------------------------------------------------


def _github(yanitlar: dict[str, httpx.Response], gorulen: list | None = None) -> GithubOAuth:
    def isle(istek: httpx.Request) -> httpx.Response:
        if gorulen is not None:
            gorulen.append(istek)
        return yanitlar[f"{istek.url.host}{istek.url.path}"]

    return GithubOAuth(OAuthAyari("kimlik", "gizli", 5, httpx.MockTransport(isle)))


def test_github_yetki_adresi_kapsam_ve_durum_tasir():
    adres = urlparse(_github({}).yetki_adresi("DURUM", "http://x/hesap-baglama/github"))
    sorgu = parse_qs(adres.query)
    assert adres.netloc == "github.com"
    assert (sorgu["client_id"], sorgu["scope"], sorgu["state"]) == (
        ["kimlik"],
        ["read:user"],
        ["DURUM"],
    )


def test_github_kodu_kimlige_cevirir_token_saklamaz():
    gorulen: list[httpx.Request] = []
    saglayici = _github(
        {
            "github.com/login/oauth/access_token": httpx.Response(
                200, json={"access_token": "gizli-token", "token_type": "bearer"}
            ),
            "api.github.com/user": httpx.Response(200, json={"login": "elif", "id": 42}),
        },
        gorulen,
    )
    dis = asyncio.run(saglayici.hesabi_oku("KOD", "http://x/hesap-baglama/github"))
    assert dis == DisHesap(kullanici_adi="elif", dis_kimlik="42")
    assert gorulen[1].headers["Authorization"] == "Bearer gizli-token"


@pytest.mark.parametrize(
    "yanit",
    [
        httpx.Response(200, json={"error": "bad_verification_code"}),
        httpx.Response(400, json={"error": "invalid_grant"}),
    ],
)
def test_github_reddedilen_kod(yanit):
    saglayici = _github({"github.com/login/oauth/access_token": yanit})
    with pytest.raises(OAuthReddedildi):
        asyncio.run(saglayici.hesabi_oku("KOD", "http://x"))


def test_gitlab_kodu_kimlige_cevirir():
    def isle(istek: httpx.Request) -> httpx.Response:
        if istek.url.path == "/oauth/token":
            assert b"grant_type=authorization_code" in istek.content
            return httpx.Response(200, json={"access_token": "t"})
        return httpx.Response(200, json={"username": "elif", "id": 7})

    saglayici = GitlabOAuth(OAuthAyari("k", "g", 5, httpx.MockTransport(isle)))
    assert "scope=read_user" in saglayici.yetki_adresi("D", "http://x")
    dis = asyncio.run(saglayici.hesabi_oku("KOD", "http://x"))
    assert dis == DisHesap(kullanici_adi="elif", dis_kimlik="7")


def test_orcid_token_yanitindaki_idyi_okur():
    def isle(istek: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"access_token": "t", "orcid": "0000-0002-1825-0097", "name": "Elif"}
        )

    saglayici = OrcidOAuth(OAuthAyari("k", "g", 5, httpx.MockTransport(isle)))
    assert "scope=%2Fauthenticate" in saglayici.yetki_adresi("D", "http://x")
    dis = asyncio.run(saglayici.hesabi_oku("KOD", "http://x"))
    assert dis == DisHesap(kullanici_adi="0000-0002-1825-0097", dis_kimlik="0000-0002-1825-0097")


def test_kurulum_yalnizca_ayari_tam_saglayicilari_acar():
    ayar = get_settings().model_copy(
        update={
            "github_oauth_istemci": "k",
            "github_oauth_gizli": "g",
            "gitlab_oauth_istemci": "k",
            "gitlab_oauth_gizli": "",
            "orcid_oauth_istemci": "k",
            "orcid_oauth_gizli": "g",
        }
    )
    assert sorted(oauth_saglayicilarini_sec(ayar)) == ["github", "orcid"]
    bos = get_settings().model_copy(update={"github_oauth_istemci": ""})
    assert "github" not in oauth_saglayicilarini_sec(bos)


# --- Uçlar ---------------------------------------------------------------------------------


class SahteOAuth:
    saglayici = "github"

    def __init__(self) -> None:
        self.dis = DisHesap(kullanici_adi="elif", dis_kimlik="42")
        self.hata: Exception | None = None

    def yetki_adresi(self, durum: str, donus_adresi: str) -> str:
        return f"https://github.com/login/oauth/authorize?state={durum}&redirect_uri={donus_adresi}"

    async def hesabi_oku(self, kod: str, donus_adresi: str) -> DisHesap:
        if self.hata is not None:
            raise self.hata
        return self.dis


@pytest.fixture
def github(oauth_saglayicilari):
    sahte = SahteOAuth()
    oauth_saglayicilari["github"] = sahte
    return sahte


async def _durum(istemci, kisi) -> str:
    yanit = await istemci.post("/hesap-baglama/oauth/github/baslat", headers=kisi.baslik)
    assert yanit.status_code == 200
    sorgu = parse_qs(urlparse(yanit.json()["yetki_adresi"]).query)
    assert sorgu["redirect_uri"][0].endswith("/hesap-baglama/github")
    return sorgu["state"][0]


async def _tamamla(istemci, kisi, durum: str):
    return await istemci.post(
        "/hesap-baglama/oauth/github/tamamla",
        headers=kisi.baslik,
        json={"kod": "KOD", "durum": durum},
    )


def test_baglama_akisi_ve_arka_planda_yeniden_okuma(github, kalemleri_yeniden_okuma_arka_plani_yok):
    async def adimlar(istemci, d):
        yanit = await _tamamla(istemci, d.genc1, await _durum(istemci, d.genc1))
        assert yanit.status_code == 201
        assert (yanit.json()["saglayici"], yanit.json()["kullanici_adi"]) == ("github", "elif")
        assert kalemleri_yeniden_okuma_arka_plani_yok == [d.K1.id]

        liste = (await istemci.get("/hesap-baglama", headers=d.genc1.baslik)).json()
        assert liste["oauth_saglayicilari"] == ["github"]
        assert [(h["saglayici"], h["yontem"]) for h in liste["hesaplar"]] == [("github", "oauth")]

        # Aynı hesabı yeniden bağlamak yan etkisiz (tek satır, ad tazelenir).
        github.dis = DisHesap(kullanici_adi="elif-yeni", dis_kimlik="42")
        yanit = await _tamamla(istemci, d.genc1, await _durum(istemci, d.genc1))
        assert (yanit.status_code, yanit.json()["kullanici_adi"]) == (201, "elif-yeni")
        sayi = await d.oturum.scalar(
            select(func.count()).where(BagliHesap.kullanici_id == d.genc1.profil.id)
        )
        assert sayi == 1

    senaryo(adimlar)


def test_baskasina_bagli_hesap_409(github):
    async def adimlar(istemci, d):
        assert (await _tamamla(istemci, d.genc1, await _durum(istemci, d.genc1))).status_code == 201
        yanit = await _tamamla(istemci, d.genc2, await _durum(istemci, d.genc2))
        assert yanit.status_code == 409

    senaryo(adimlar)


def test_durum_baska_hesabin_ya_da_sahte_ise_400(github):
    async def adimlar(istemci, d):
        durum = await _durum(istemci, d.genc1)
        assert (await _tamamla(istemci, d.genc2, durum)).status_code == 400
        assert (await _tamamla(istemci, d.genc1, "sahte")).status_code == 400

    senaryo(adimlar)


@pytest.mark.parametrize(
    ("hata", "kod"),
    [(OAuthReddedildi("github"), 400), (TimeoutError(), 503), (httpx.ConnectError("x"), 503)],
)
def test_saglayici_hatalari(github, hata, kod):
    async def adimlar(istemci, d):
        github.hata = hata
        assert (await _tamamla(istemci, d.genc1, await _durum(istemci, d.genc1))).status_code == kod

    senaryo(adimlar)


def test_kapali_saglayici_404_ve_yetki():
    async def adimlar(istemci, d):
        yol = "/hesap-baglama/oauth/github/baslat"
        await durumlar(istemci, "POST", yol, {None: 401, d.kurum1: 403, d.girvak: 403})
        await durumlar(istemci, "POST", yol, {d.genc1: 404})
        await durumlar(istemci, "GET", "/hesap-baglama", {None: 401, d.kurum1: 403, d.genc1: 200})

    senaryo(adimlar)


def test_baglantiyi_kaldirma_sahibi_yapar(github, kalemleri_yeniden_okuma_arka_plani_yok):
    async def adimlar(istemci, d):
        bagli = (await _tamamla(istemci, d.genc1, await _durum(istemci, d.genc1))).json()
        yol = f"/hesap-baglama/{bagli['id']}"
        await durumlar(istemci, "DELETE", yol, {None: 401, d.kurum1: 403, d.genc2: 404})
        yanit = await istemci.delete(yol, headers=d.genc1.baslik)
        assert (yanit.status_code, yanit.json()["hesaplar"]) == (200, [])
        await durumlar(istemci, "DELETE", yol, {d.genc1: 404})
        assert kalemleri_yeniden_okuma_arka_plani_yok == [d.K1.id, d.K1.id]

    senaryo(adimlar)
