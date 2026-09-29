"""Genç kayıt formu ve profil düzenleme (docs/plans/genc-akisi.md § 5.1, § 6.1)."""

import asyncio
import datetime as dt
import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.auth import hesap_olustur
from app.api.profil import bosaltilan_zorunlular
from app.core.genc_profili import (
    eksik_profil_alanlari,
    mezuniyet_yili_dogrula,
    sehir_dogrula,
    url_dogrula,
)
from app.core.kimlik import token_uret
from app.main import app
from app.schemas.auth import KayitIstegi
from app.schemas.profil import GencKayitProfili
from tests.sahte_hesap import FIRMA_KAYIT_EKI, GENC_KAYIT_EKI
from tests.veritabani import api_istemcisi, geri_alinan_oturum

PROFIL = GENC_KAYIT_EKI["genc_profili"]


# --- Saf kurallar ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("girdi", "beklenen"),
    [
        ("github.com/elif", "https://github.com/elif"),
        ("https://elif.dev", "https://elif.dev"),
        ("http://ornek.org/portfolyo", "http://ornek.org/portfolyo"),
        ("  ", None),
        (None, None),
    ],
)
def test_url_tamamlanir(girdi, beklenen):
    assert url_dogrula(girdi) == beklenen


@pytest.mark.parametrize("girdi", ["ftp://ornek.org", "benim sitem", "localhost", "https://"])
def test_gecersiz_url_reddedilir(girdi):
    with pytest.raises(ValueError):
        url_dogrula(girdi)


def test_sehir_kanonik_ve_kati():
    assert sehir_dogrula("istanbul") == "İstanbul"
    assert sehir_dogrula("") is None
    with pytest.raises(ValueError):
        sehir_dogrula("Narnia")
    with pytest.raises(ValueError):
        sehir_dogrula("uzaktan")  # şehir değil, çalışma modeli


def test_mezuniyet_yili_araligi():
    bugun = dt.date(2026, 9, 28)
    assert mezuniyet_yili_dogrula(2028, bugun) == 2028
    with pytest.raises(ValueError):
        mezuniyet_yili_dogrula(1900, bugun)
    with pytest.raises(ValueError):
        mezuniyet_yili_dogrula(2040, bugun)


def test_eksik_profil_alanlari_sirali():
    assert eksik_profil_alanlari(
        sehir=None, calisma_modelleri=[], musaitlikler=["staj"], kariyer_durumu=None
    ) == ["sehir", "calisma_modelleri", "kariyer_durumu"]
    assert (
        eksik_profil_alanlari(
            sehir="İzmir",
            calisma_modelleri=["uzaktan"],
            musaitlikler=["staj"],
            kariyer_durumu="mezun",
        )
        == []
    )


def test_zorunlu_alan_bosaltilamaz_opsiyonel_bosaltilabilir():
    assert bosaltilan_zorunlular({"sehir": None, "musaitlikler": [], "okul": None}) == [
        "musaitlikler",
        "sehir",
    ]
    assert bosaltilan_zorunlular({"github_url": None, "okul": None}) == []


# --- Şema -----------------------------------------------------------------------------------


def _kayit(**ek):
    return {"email": "e@ornek.com", "sifre": "yeterince-uzun", "ad": "Elif", **ek}


def test_genc_kaydi_profil_ve_kvkk_ister():
    with pytest.raises(ValidationError, match="profil"):
        KayitIstegi(**_kayit(rol="genc", kvkk_onay=True))
    with pytest.raises(ValidationError, match="KVKK"):
        KayitIstegi(**_kayit(rol="genc", genc_profili=PROFIL, kvkk_onay=False))
    assert KayitIstegi(**_kayit(rol="genc", **GENC_KAYIT_EKI)).genc_profili.sehir == "İstanbul"


def test_kurum_kaydi_genc_profili_tasimaz():
    # Firma kaydı artık firma profili ve KVKK onayı ister (firma-akisi § 0 karar 2).
    assert KayitIstegi(**_kayit(rol="kurum", **FIRMA_KAYIT_EKI)).genc_profili is None
    with pytest.raises(ValidationError):
        KayitIstegi(**_kayit(rol="kurum", genc_profili=PROFIL, **FIRMA_KAYIT_EKI))


@pytest.mark.parametrize(
    ("alan", "deger"),
    [
        ("calisma_modelleri", []),
        ("calisma_modelleri", ["evden"]),
        ("musaitlikler", []),
        ("musaitlikler", ["haftasonu"]),
        ("kariyer_durumu", "issiz"),
        ("sehir", "Narnia"),
        ("sinif", 9),
        ("github_url", "benim sitem"),
    ],
)
def test_gecersiz_profil_alani_reddedilir(alan, deger):
    with pytest.raises(ValidationError):
        GencKayitProfili(**{**PROFIL, alan: deger})


@pytest.mark.parametrize(
    "toplanmayan", ["cinsiyet", "dogum_tarihi", "yas", "tc_kimlik_no", "adres", "ucret_beklentisi"]
)
def test_toplanmayan_alan_422(toplanmayan):
    """Bilinçli olarak toplanmayan alanlar sessizce yok sayılmaz, reddedilir."""
    with pytest.raises(ValidationError):
        GencKayitProfili(**{**PROFIL, toplanmayan: "x"})


def test_profilsiz_genc_kaydi_ucta_422():
    yanit = TestClient(app).post(
        "/auth/kayit", json=_kayit(rol="genc", email="p@ornek.com", kvkk_onay=True)
    )
    assert yanit.status_code == 422


# --- Gerçek veritabanında -------------------------------------------------------------------


def _email() -> str:
    return f"test-{uuid.uuid4().hex[:10]}@ornek.com"


def _baslik(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_kayit_profili_ve_kvkk_onayini_yazar():
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            kayit = await istemci.post(
                "/auth/kayit",
                json={
                    "email": _email(),
                    "sifre": "yeterince-uzun",
                    "rol": "genc",
                    "ad": "Elif",
                    "kvkk_onay": True,
                    "genc_profili": {
                        **PROFIL,
                        "sehir": "izmir",
                        "calisma_modelleri": ["uzaktan", "hibrit"],
                        "musaitlikler": ["staj", "proje_bazli"],
                        "okul": "  Ege   Üniversitesi ",
                        "sinif": 3,
                        "github_url": "github.com/elif",
                    },
                },
            )
            assert kayit.status_code == 201
            token = kayit.json()["token"]

            profil = (await istemci.get("/profil", headers=_baslik(token))).json()
            assert profil["sehir"] == "İzmir"
            assert profil["calisma_modelleri"] == ["hibrit", "uzaktan"]  # sabit sıra
            assert profil["musaitlikler"] == ["proje_bazli", "staj"]
            assert profil["okul"] == "Ege Üniversitesi"
            assert profil["github_url"] == "https://github.com/elif"
            assert profil["kvkk_onay_tarihi"] is not None
            assert profil["eksik_alanlar"] == []

            me = (await istemci.get("/me", headers=_baslik(token))).json()
            assert me["eksik_profil_alanlari"] == []
            assert me["kvkk_onayli"] is True

    asyncio.run(senaryo())


def test_eski_hesap_eksik_alanlari_ve_kvkk_onayi_ister():
    """Bu alanlardan önce açılmış hesap: /me bant için eksikleri söyler."""

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap = await hesap_olustur(
                oturum, email=_email(), sifre="yeterince-uzun", rol="genc", ad="Eski"
            )
            token = token_uret(hesap.id, "genc")
            me = (await istemci.get("/me", headers=_baslik(token))).json()
            assert me["eksik_profil_alanlari"] == [
                "sehir",
                "calisma_modelleri",
                "musaitlikler",
                "kariyer_durumu",
            ]
            assert me["kvkk_onayli"] is False

            guncel = await istemci.patch(
                "/profil",
                headers=_baslik(token),
                json={**PROFIL, "kvkk_onay": True},
            )
            assert guncel.status_code == 200
            me = (await istemci.get("/me", headers=_baslik(token))).json()
            assert me["eksik_profil_alanlari"] == []
            assert me["kvkk_onayli"] is True

    asyncio.run(senaryo())


def test_patch_yalnizca_gonderileni_degistirir_zorunluyu_bosaltmaz():
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            kayit = await istemci.post(
                "/auth/kayit",
                json={
                    "email": _email(),
                    "sifre": "yeterince-uzun",
                    "rol": "genc",
                    "ad": "Elif",
                    "kvkk_onay": True,
                    "genc_profili": {**PROFIL, "github_url": "github.com/elif", "okul": "ODTÜ"},
                },
            )
            baslik = _baslik(kayit.json()["token"])

            yanit = await istemci.patch(
                "/profil", headers=baslik, json={"github_url": "", "musaitlikler": ["staj"]}
            )
            assert yanit.status_code == 200
            govde = yanit.json()
            assert govde["github_url"] is None  # opsiyonel alan silindi
            assert govde["musaitlikler"] == ["staj"]
            assert govde["okul"] == "ODTÜ"  # gönderilmedi, değişmedi
            assert govde["sehir"] == "İstanbul"

            bos = await istemci.patch("/profil", headers=baslik, json={"sehir": None})
            assert bos.status_code == 422
            toplanmayan = await istemci.patch("/profil", headers=baslik, json={"cinsiyet": "k"})
            assert toplanmayan.status_code == 422

    asyncio.run(senaryo())


def test_profil_uclari_yetki():
    """401 token yok, 403 genç değil. Başkasının profili diye bir yol yok (token'ın profili)."""

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            kurum = await hesap_olustur(
                oturum, email=_email(), sifre="yeterince-uzun", rol="kurum", ad="Koop"
            )
            assert (await istemci.get("/profil")).status_code == 401
            assert (await istemci.patch("/profil", json={"okul": "x"})).status_code == 401
            kurum_basligi = _baslik(token_uret(kurum.id, "kurum"))
            assert (await istemci.get("/profil", headers=kurum_basligi)).status_code == 403
            assert (
                await istemci.patch("/profil", headers=kurum_basligi, json={"okul": "x"})
            ).status_code == 403

    asyncio.run(senaryo())
