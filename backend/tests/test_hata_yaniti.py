"""Hata yanıtlarının biçimi ve CORS başlıkları.

Yakalanmayan bir hata tarayıcıya "sunucuya ulaşılamadı" gibi görünmemeli:
CORS başlığı olmayan bir 500, fetch tarafında ağ hatasından ayırt edilemiyor.
"""

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.core.hatalar import BEKLENMEYEN_MESAJ, MESGUL_MESAJI, hata_isleyicilerini_kur
from app.core.llm import HizSinirHatasi, ModelMesgulHatasi

ORIGIN = "http://localhost:3000"


@pytest.fixture
def istemci() -> TestClient:
    app = FastAPI()
    app.add_middleware(CORSMiddleware, allow_origins=[ORIGIN], allow_credentials=True)
    hata_isleyicilerini_kur(app)

    @app.get("/patla")
    async def patla():
        raise RuntimeError("veritabanı bağlantısı koptu")

    @app.get("/kota")
    async def kota():
        raise HizSinirHatasi("429 RESOURCE_EXHAUSTED")

    @app.get("/mesgul")
    async def mesgul():
        raise ModelMesgulHatasi("503 UNAVAILABLE")

    return TestClient(app, raise_server_exceptions=False)


def test_beklenmeyen_hata_json_doner(istemci):
    yanit = istemci.get("/patla", headers={"Origin": ORIGIN})
    assert yanit.status_code == 500
    assert yanit.json() == {"detail": BEKLENMEYEN_MESAJ}


def test_beklenmeyen_hata_cors_basligi_tasir(istemci):
    """Bu başlık olmadan tarayıcı yanıtı hiç okuyamıyor."""
    yanit = istemci.get("/patla", headers={"Origin": ORIGIN})
    assert yanit.headers["access-control-allow-origin"] == ORIGIN


def test_ic_ayrinti_kullaniciya_sizmaz(istemci):
    yanit = istemci.get("/patla", headers={"Origin": ORIGIN})
    assert "veritabanı" not in yanit.text


def test_izinsiz_origin_cors_basligi_almaz(istemci):
    yanit = istemci.get("/patla", headers={"Origin": "http://kotu.example"})
    assert "access-control-allow-origin" not in yanit.headers
    assert yanit.status_code == 500


def test_kota_hatasi_429_doner(istemci):
    yanit = istemci.get("/kota", headers={"Origin": ORIGIN})
    assert yanit.status_code == 429
    assert yanit.headers["access-control-allow-origin"] == ORIGIN


def test_mesgul_model_503_doner(istemci):
    """Geçici yoğunluk, kotadan ayrı bir şey söylüyor."""
    yanit = istemci.get("/mesgul", headers={"Origin": ORIGIN})
    assert yanit.status_code == 503
    assert yanit.json() == {"detail": MESGUL_MESAJI}
