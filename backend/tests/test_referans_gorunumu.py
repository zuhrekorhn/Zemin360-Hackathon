"""Referans kişinin girişsiz sayfada gördüğü bilgi.

Bu uç nokta kimlik doğrulamıyor — elinde token olan herkes açabiliyor.
O yüzden ne döndürdüğü kadar ne DÖNDÜRMEDİĞİ de test ediliyor.
"""

import datetime as dt
import uuid
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from app.agents.dogrulama import DURUM_BEKLIYOR, DURUM_YANIT_YOK, DURUM_YANITLANDI
from app.api.dogrulama import referans_gorunumu
from app.db.session import get_session
from app.main import app
from app.schemas.dogrulama import ReferansIstegiYaniti

IDDIA_SAHIBI = "Elif Şahin"
EMAIL = "elif@ornek.com"


@dataclass
class SahteKullanici:
    ad: str = IDDIA_SAHIBI
    email: str = EMAIL


@dataclass
class SahteKart:
    kullanici: SahteKullanici = field(default_factory=SahteKullanici)


@dataclass
class SahteCikti:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    baslik: str = "Mahalle kütüphanesi ödünç takip sistemi"
    aciklama: str | None = "400 kitabı ve 120 üyeyi takip ediyor."
    yetenek_karti: SahteKart = field(default_factory=SahteKart)


@dataclass
class SahteReferans:
    durum: str = DURUM_BEKLIYOR
    olusturma_tarihi: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.UTC))
    somut_cikti: SahteCikti = field(default_factory=SahteCikti)


class SahteOturum:
    """`scalar()` çağrısına hazır cevabı veren oturum taklidi (DB'siz test)."""

    def __init__(self, sonuc):
        self.sonuc = sonuc
        self.commit_sayisi = 0

    async def scalar(self, *_args, **_kwargs):
        return self.sonuc

    async def commit(self):
        self.commit_sayisi += 1


def istemci(sonuc) -> TestClient:
    oturum = SahteOturum(sonuc)
    app.dependency_overrides[get_session] = lambda: oturum
    return TestClient(app)


@pytest.fixture(autouse=True)
def _temizle():
    yield
    app.dependency_overrides.clear()


def test_iddia_referans_kisiye_gosteriliyor():
    """Neyi onayladığını görmeden puan vermek anlamsız."""
    gorunum = referans_gorunumu(SahteReferans())
    assert gorunum.baslik == "Mahalle kütüphanesi ödünç takip sistemi"
    assert gorunum.aciklama is not None
    assert gorunum.iddia_sahibi_adi == IDDIA_SAHIBI


def test_iletisim_bilgisi_donmuyor():
    """Girişsiz uç nokta: ad yeterli, e-posta ve telefon burada işi yok."""
    alanlar = set(ReferansIstegiYaniti.model_fields)
    assert not {"email", "iletisim_email", "telefon"} & alanlar

    yanit = istemci(SahteReferans()).get("/dogrulama/referans/token-123")
    assert yanit.status_code == 200
    assert EMAIL not in yanit.text


def test_bekleyen_referans_yanitlanabilir():
    yanit = istemci(SahteReferans()).get("/dogrulama/referans/token-123")
    govde = yanit.json()
    assert govde["durum"] == DURUM_BEKLIYOR
    assert govde["yanitlanabilir"] is True


def test_yanitlanmis_referans_tekrar_yanitlanamaz():
    """Form gösterilmesin: tek kullanımlık link zaten harcanmış."""
    govde = (
        istemci(SahteReferans(durum=DURUM_YANITLANDI)).get("/dogrulama/referans/token-123").json()
    )
    assert govde["durum"] == DURUM_YANITLANDI
    assert govde["yanitlanabilir"] is False


def test_suresi_gecmis_link_okuma_aninda_kapanir():
    """Zaman aşımı için zamanlayıcı yok; bu okuma anında hesaplanıyor."""
    eski = SahteReferans(olusturma_tarihi=dt.datetime.now(dt.UTC) - dt.timedelta(days=30))
    govde = istemci(eski).get("/dogrulama/referans/token-123").json()
    assert govde["durum"] == DURUM_YANIT_YOK
    assert govde["yanitlanabilir"] is False


def test_gecersiz_token_404_doner():
    yanit = istemci(None).get("/dogrulama/referans/olmayan-token")
    assert yanit.status_code == 404
