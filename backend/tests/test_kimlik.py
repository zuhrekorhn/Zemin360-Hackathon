"""Kimlik: şifre hash'i, JWT, kayıt, giriş, /me (docs/kimlik-ve-dongu.md § 1-2).

Saf kısımlar ağsız; kayıt/giriş/me yerel veritabanında geri alınan bir işlem
içinde (tests/veritabani.py), veritabanı yoksa atlanır.
"""

import asyncio
import datetime as dt
import uuid

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.auth import EPOSTA_KAYITLI, GIRIS_HATALI, hesap_olustur
from app.api.kimlik import ROL_UYGUN_DEGIL, mevcut_hesap, rol_gerekli
from app.core.config import get_settings
from app.core.kimlik import (
    TOKEN_OMRU,
    TokenGecersiz,
    sifre_dogru_mu,
    sifre_hashle,
    token_coz,
    token_uret,
)
from tests.sahte_hesap import FIRMA_KAYIT_EKI, GENC_KAYIT_EKI
from tests.veritabani import api_istemcisi, geri_alinan_oturum

# --- Şifre ---------------------------------------------------------------------------


def test_sifre_duz_saklanmaz_ve_dogrulanir():
    hash_ = sifre_hashle("gizli-sifre-123")
    assert "gizli-sifre-123" not in hash_
    assert hash_.startswith("$argon2id$")
    assert sifre_dogru_mu(hash_, "gizli-sifre-123")
    assert not sifre_dogru_mu(hash_, "yanlis-sifre")


def test_hesap_yoksa_dogrulama_basarisiz_ama_cokmez():
    """Olmayan hesapta da karşılaştırma yapılır (zamanlama e-postayı ele vermesin)."""
    assert not sifre_dogru_mu(None, "herhangi")


# --- Token -----------------------------------------------------------------------------


def test_token_icerigi_geri_okunur():
    hesap_id = uuid.uuid4()
    icerik = token_coz(token_uret(hesap_id, "kurum"))
    assert icerik.hesap_id == hesap_id
    assert icerik.rol == "kurum"


def test_token_yedi_gun_gecerli():
    an = dt.datetime.now(dt.UTC)
    icerik = jwt.decode(
        token_uret(uuid.uuid4(), "genc", simdi=an),
        get_settings().jwt_gizli_anahtar,
        algorithms=["HS256"],
    )
    assert icerik["exp"] - icerik["iat"] == int(TOKEN_OMRU.total_seconds())


def test_suresi_dolmus_token_reddedilir():
    eski = dt.datetime.now(dt.UTC) - TOKEN_OMRU - dt.timedelta(minutes=1)
    with pytest.raises(TokenGecersiz):
        token_coz(token_uret(uuid.uuid4(), "genc", simdi=eski))


def test_baska_anahtarla_imzalanmis_token_reddedilir():
    sahte = jwt.encode(
        {"sub": str(uuid.uuid4()), "rol": "girvak", "iat": 0, "exp": 9999999999},
        "baska-bir-anahtar-baska-bir-anahtar-123",
        algorithm="HS256",
    )
    with pytest.raises(TokenGecersiz):
        token_coz(sahte)


def test_imzasiz_token_reddedilir():
    """alg=none saldırısı: imza atlanarak rol yükseltilemesin."""
    imzasiz = jwt.encode(
        {"sub": str(uuid.uuid4()), "rol": "girvak", "iat": 0, "exp": 9999999999},
        key=None,
        algorithm="none",
    )
    with pytest.raises(TokenGecersiz):
        token_coz(imzasiz)


def test_eksik_claimli_token_reddedilir():
    eksik = jwt.encode({"sub": str(uuid.uuid4())}, get_settings().jwt_gizli_anahtar)
    with pytest.raises(TokenGecersiz):
        token_coz(eksik)


# --- Rol bağımlılığı (veritabanısız) ------------------------------------------------


def test_rol_uymazsa_403():
    uygulama = FastAPI()

    @uygulama.get("/yalniz-kurum")
    async def yalniz_kurum(hesap=Depends(rol_gerekli("kurum"))):
        return {"rol": hesap.rol}

    uygulama.dependency_overrides[mevcut_hesap] = lambda: type("H", (), {"rol": "genc"})()
    yanit = TestClient(uygulama).get("/yalniz-kurum")
    assert yanit.status_code == 403
    assert yanit.json()["detail"] == ROL_UYGUN_DEGIL

    uygulama.dependency_overrides[mevcut_hesap] = lambda: type("H", (), {"rol": "kurum"})()
    assert TestClient(uygulama).get("/yalniz-kurum").status_code == 200


# --- Kayıt ve giriş şeması (veritabanısız) -------------------------------------------


@pytest.fixture
def istemci():
    from app.main import app

    return TestClient(app)


def test_girvak_acik_kayitla_hesap_acamaz(istemci):
    yanit = istemci.post(
        "/auth/kayit",
        json={"email": "g@ornek.org", "sifre": "yeterince-uzun", "rol": "girvak", "ad": "G"},
    )
    assert yanit.status_code == 422


def test_kisa_sifre_reddedilir(istemci):
    yanit = istemci.post(
        "/auth/kayit",
        json={
            "email": "e@ornek.com",
            "sifre": "kisa",
            "rol": "genc",
            "ad": "Elif",
            **GENC_KAYIT_EKI,
        },
    )
    assert yanit.status_code == 422


def test_tokensiz_me_401_ve_bearer_ister(istemci):
    yanit = istemci.get("/me")
    assert yanit.status_code == 401
    assert yanit.headers["www-authenticate"] == "Bearer"


def test_bozuk_tokenla_me_401(istemci):
    yanit = istemci.get("/me", headers={"Authorization": "Bearer bozuk.token.degeri"})
    assert yanit.status_code == 401


# --- Gerçek veritabanında --------------------------------------------------------------


def _email() -> str:
    return f"test-{uuid.uuid4().hex[:10]}@ornek.com"


def test_genc_kaydi_hesap_ve_profil_acar_token_doner():
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            email = _email()
            kayit = await istemci.post(
                "/auth/kayit",
                json={
                    "email": email.upper(),
                    "sifre": "yeterince-uzun",
                    "rol": "genc",
                    "ad": "Elif",
                    **GENC_KAYIT_EKI,
                },
            )
            assert kayit.status_code == 201
            token = kayit.json()["token"]
            assert kayit.json()["rol"] == "genc"

            me = await istemci.get("/me", headers={"Authorization": f"Bearer {token}"})
            assert me.status_code == 200
            govde = me.json()
            assert govde["email"] == email  # normalize edildi
            assert govde["ad"] == "Elif"
            assert govde["kullanici_id"] is not None
            assert govde["kurum_id"] is None
            assert govde["yetenek_karti"] is None  # Keşif'i henüz tamamlamadı

    asyncio.run(senaryo())


def test_kurum_kaydi_kurum_profili_acar():
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            kayit = await istemci.post(
                "/auth/kayit",
                json={
                    "email": _email(),
                    "sifre": "yeterince-uzun",
                    "rol": "kurum",
                    "ad": "Koop",
                    **FIRMA_KAYIT_EKI,
                },
            )
            me = await istemci.get(
                "/me", headers={"Authorization": f"Bearer {kayit.json()['token']}"}
            )
            assert me.json()["rol"] == "kurum"
            assert me.json()["kurum_id"] is not None
            assert me.json()["ad"] == "Koop"

    asyncio.run(senaryo())


def test_ayni_eposta_ikinci_kez_kayit_olamaz_buyuk_kucuk_harf_farkiyla_da():
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            email = _email()
            govde = {"sifre": "yeterince-uzun", "rol": "genc", "ad": "Elif", **GENC_KAYIT_EKI}
            assert (
                await istemci.post("/auth/kayit", json={**govde, "email": email})
            ).status_code == 201
            ikinci = await istemci.post("/auth/kayit", json={**govde, "email": email.upper()})
            assert ikinci.status_code == 409
            assert ikinci.json()["detail"] == EPOSTA_KAYITLI

    asyncio.run(senaryo())


def test_giris_dogru_sifreyle_token_yanlisla_ayni_401():
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            email = _email()
            await istemci.post(
                "/auth/kayit",
                json={
                    "email": email,
                    "sifre": "yeterince-uzun",
                    "rol": "genc",
                    "ad": "Elif",
                    **GENC_KAYIT_EKI,
                },
            )
            dogru = await istemci.post(
                "/auth/giris", json={"email": email, "sifre": "yeterince-uzun"}
            )
            assert dogru.status_code == 200
            assert dogru.json()["rol"] == "genc"

            yanlis_sifre = await istemci.post(
                "/auth/giris", json={"email": email, "sifre": "yanlis"}
            )
            olmayan = await istemci.post(
                "/auth/giris", json={"email": _email(), "sifre": "yeterince-uzun"}
            )
            # Hangisinin yanlış olduğu söylenmez
            assert yanlis_sifre.status_code == olmayan.status_code == 401
            assert yanlis_sifre.json() == olmayan.json() == {"detail": GIRIS_HATALI}

    asyncio.run(senaryo())


def test_silinmis_hesabin_tokeni_gecersiz():
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            token = token_uret(uuid.uuid4(), "genc")  # böyle bir hesap yok
            yanit = await istemci.get("/me", headers={"Authorization": f"Bearer {token}"})
            assert yanit.status_code == 401

    asyncio.run(senaryo())


def test_rolu_tokendakiyle_uyusmayan_token_gecersiz():
    """Token'daki rol hesabın rolüyle aynı değilse (elle üretilmiş ya da eski) 401."""

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap = await hesap_olustur(
                oturum, email=_email(), sifre="yeterince-uzun", rol="genc", ad="Elif"
            )
            token = token_uret(hesap.id, "girvak")
            yanit = await istemci.get("/me", headers={"Authorization": f"Bearer {token}"})
            assert yanit.status_code == 401

    asyncio.run(senaryo())


def test_girvak_hesabi_betik_fonksiyonuyla_acilir_profilsizdir():
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap = await hesap_olustur(
                oturum, email=_email(), sifre="yeterince-uzun", rol="girvak", ad=None
            )
            token = token_uret(hesap.id, "girvak")
            me = (await istemci.get("/me", headers={"Authorization": f"Bearer {token}"})).json()
            assert me["rol"] == "girvak"
            assert me["kullanici_id"] is None and me["kurum_id"] is None

    asyncio.run(senaryo())
