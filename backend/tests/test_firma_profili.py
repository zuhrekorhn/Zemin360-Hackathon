"""Firma kayıt formu ve profili (docs/kararlar.md F1-2, 9; § 2)."""

from __future__ import annotations

import asyncio
import datetime as dt
import uuid

import pytest
from pydantic import ValidationError

from app.api.auth import hesap_olustur
from app.core.firma_profili import (
    FIRMA_TURLERI,
    eksik_firma_alanlari,
    kurulus_yili_dogrula,
    tanitim_temizle,
)
from app.core.kimlik import token_uret
from app.schemas.auth import KayitIstegi
from app.schemas.profil import FirmaKayitProfili, FirmaProfilGuncelleme
from tests.sahte_hesap import FIRMA_KAYIT_EKI, GENC_KAYIT_EKI
from tests.veritabani import api_istemcisi, geri_alinan_oturum

FIRMA = FIRMA_KAYIT_EKI["firma_profili"]


def _email() -> str:
    return f"firma-{uuid.uuid4().hex[:10]}@ornek.com"


def _baslik(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _kayit(**ek):
    return {"email": _email(), "sifre": "yeterince-uzun", "ad": "Market X", **ek}


# --- Saf kurallar ----------------------------------------------------------------------


def test_firma_turleri():
    assert FIRMA_TURLERI == ("girisim", "kobi", "kurumsal")


def test_kurulus_yili():
    bugun = dt.date(2026, 9, 30)
    assert kurulus_yili_dogrula(None, bugun) is None
    assert kurulus_yili_dogrula(2019, bugun) == 2019
    for yil in (1899, 2027):
        with pytest.raises(ValueError, match="Kuruluş yılı"):
            kurulus_yili_dogrula(yil, bugun)


def test_tanitim():
    assert tanitim_temizle("  ") is None
    assert tanitim_temizle("Zincir\n market. ") == "Zincir market."
    with pytest.raises(ValueError, match="300"):
        tanitim_temizle("a" * 301)


def test_eksik_firma_alanlari_sabit_sirada():
    assert eksik_firma_alanlari(tur=None, sektor="", sehir=None) == ["tur", "sektor", "sehir"]
    assert eksik_firma_alanlari(tur="kobi", sektor="Gıda", sehir="İzmir") == []


# --- Şemalar ---------------------------------------------------------------------------


def test_firma_kayit_profili_zorunlular_ve_normalize():
    profil = FirmaKayitProfili(
        tur="girisim", sektor="  Yapay  zekâ ", sehir="istanbul", web_sitesi="marketx.com"
    )
    assert profil.sektor == "Yapay zekâ"
    assert profil.sehir == "İstanbul"
    assert profil.web_sitesi == "https://marketx.com"
    for eksik in ("tur", "sektor", "sehir"):
        with pytest.raises(ValidationError):
            FirmaKayitProfili(**{k: v for k, v in FIRMA.items() if k != eksik})


@pytest.mark.parametrize(
    ("alan", "deger"),
    [
        ("tur", "dernek"),
        ("sehir", "Atlantis"),
        ("calisan_araligi", "10-20"),
        ("kurulus_yili", 1800),
        ("web_sitesi", "market x"),
        # Bilinçli olarak toplanmayan alanlar (docs/kararlar.md F2): sessizce yok sayılmaz.
        ("vergi_no", "1234567890"),
        ("telefon", "5551234567"),
        ("adres", "Bir sokak"),
    ],
)
def test_firma_kayit_profili_gecersizleri_reddeder(alan, deger):
    with pytest.raises(ValidationError):
        FirmaKayitProfili(**{**FIRMA, alan: deger})


def test_firma_kaydi_profil_ve_kvkk_ister():
    with pytest.raises(ValidationError, match="firma bilgileri"):
        KayitIstegi(**_kayit(rol="kurum", kvkk_onay=True))
    with pytest.raises(ValidationError, match="KVKK"):
        KayitIstegi(**_kayit(rol="kurum", firma_profili=FIRMA))
    with pytest.raises(ValidationError, match="firma profili"):
        KayitIstegi(**_kayit(rol="genc", firma_profili=FIRMA, **GENC_KAYIT_EKI))
    assert KayitIstegi(**_kayit(rol="kurum", **FIRMA_KAYIT_EKI)).firma_profili.tur == "kobi"


def test_guncelleme_toplanmayan_alani_reddeder():
    with pytest.raises(ValidationError):
        FirmaProfilGuncelleme(vergi_no="1")


# --- Gerçek veritabanı -----------------------------------------------------------------


def test_firma_kaydi_profili_yazar_me_bant_istemez():
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            kayit = await istemci.post(
                "/auth/kayit",
                json=_kayit(
                    rol="kurum",
                    kvkk_onay=True,
                    firma_profili={
                        **FIRMA,
                        "web_sitesi": "marketx.com",
                        "calisan_araligi": "51-250",
                        "kurulus_yili": 2010,
                        "tanitim": "Zincir market.",
                        "yetkili_ad": "Ayşe Kaya",
                        "yetkili_gorev": "İnovasyon müdürü",
                    },
                ),
            )
            assert kayit.status_code == 201
            baslik = _baslik(kayit.json()["token"])

            me = (await istemci.get("/me", headers=baslik)).json()
            assert me["eksik_profil_alanlari"] == []
            assert me["kvkk_onayli"] is True

            profil = (await istemci.get("/kurum/profil", headers=baslik)).json()
            assert profil["tur"] == "kobi"
            assert profil["web_sitesi"] == "https://marketx.com"
            assert profil["calisan_araligi"] == "51-250"
            assert profil["kurulus_yili"] == 2010
            assert profil["yetkili_gorev"] == "İnovasyon müdürü"
            assert profil["kvkk_onay_tarihi"] is not None
            assert profil["eksik_alanlar"] == []

    asyncio.run(senaryo())


def test_firma_kaydi_profilsiz_ya_da_kvkksiz_422():
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            profilsiz = await istemci.post("/auth/kayit", json=_kayit(rol="kurum", kvkk_onay=True))
            assert profilsiz.status_code == 422
            kvkksiz = await istemci.post(
                "/auth/kayit", json=_kayit(rol="kurum", firma_profili=FIRMA)
            )
            assert kvkksiz.status_code == 422

    asyncio.run(senaryo())


def test_eski_firma_hesabi_bant_ve_tamamlama():
    """Bu alanlardan önce açılmış firma: /me bant için eksikleri söyler (docs/kararlar.md F9)."""

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap = await hesap_olustur(
                oturum, email=_email(), sifre="yeterince-uzun", rol="kurum", ad="Eski Koop"
            )
            baslik = _baslik(token_uret(hesap.id, "kurum"))
            me = (await istemci.get("/me", headers=baslik)).json()
            assert me["eksik_profil_alanlari"] == ["tur", "sektor", "sehir"]
            assert me["kvkk_onayli"] is False

            guncel = await istemci.patch(
                "/kurum/profil", headers=baslik, json={**FIRMA, "kvkk_onay": True}
            )
            assert guncel.status_code == 200
            me = (await istemci.get("/me", headers=baslik)).json()
            assert me["eksik_profil_alanlari"] == []
            assert me["kvkk_onayli"] is True

    asyncio.run(senaryo())


def test_patch_yalnizca_gonderileni_degistirir_zorunluyu_bosaltmaz():
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            kayit = await istemci.post(
                "/auth/kayit",
                json=_kayit(
                    rol="kurum",
                    kvkk_onay=True,
                    firma_profili={**FIRMA, "tanitim": "Eski tanıtım", "kurulus_yili": 2001},
                ),
            )
            baslik = _baslik(kayit.json()["token"])

            yanit = await istemci.patch(
                "/kurum/profil",
                headers=baslik,
                json={"tanitim": "", "tur": "girisim", "ad": "Market X Teknoloji"},
            )
            assert yanit.status_code == 200
            govde = yanit.json()
            assert govde["tanitim"] is None  # isteğe bağlı alan silindi
            assert govde["tur"] == "girisim"
            assert govde["ad"] == "Market X Teknoloji"
            assert govde["kurulus_yili"] == 2001  # gönderilmedi, değişmedi

            for bos in ({"sehir": None}, {"tur": None}, {"sektor": ""}, {"ad": " "}):
                cevap = await istemci.patch("/kurum/profil", headers=baslik, json=bos)
                assert cevap.status_code == 422, bos
            toplanmayan = await istemci.patch(
                "/kurum/profil", headers=baslik, json={"vergi_no": "1"}
            )
            assert toplanmayan.status_code == 422

    asyncio.run(senaryo())


def test_firma_profili_uclari_yetki():
    """401 token yok, 403 firma değil. Başkasının profili diye bir yol yok (token'ın profili)."""

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            genc = await hesap_olustur(
                oturum, email=_email(), sifre="yeterince-uzun", rol="genc", ad="Elif"
            )
            assert (await istemci.get("/kurum/profil")).status_code == 401
            assert (await istemci.patch("/kurum/profil", json={"tanitim": "x"})).status_code == 401
            genc_basligi = _baslik(token_uret(genc.id, "genc"))
            assert (await istemci.get("/kurum/profil", headers=genc_basligi)).status_code == 403
            assert (
                await istemci.patch("/kurum/profil", headers=genc_basligi, json={"tanitim": "x"})
            ).status_code == 403

    asyncio.run(senaryo())
