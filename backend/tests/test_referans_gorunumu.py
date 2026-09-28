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


def test_suresi_gecmis_linke_yanit_verilemez():
    """GET "yanıtlanamaz" derken POST kabul etmemeli: aynı kural, iki uç nokta."""
    eski = SahteReferans(olusturma_tarihi=dt.datetime.now(dt.UTC) - dt.timedelta(days=30))
    yanit = istemci(eski).post(
        "/dogrulama/referans-yaniti",
        json={"token": "token-123", "puan": 5, "yorum": "harika"},
    )
    assert yanit.status_code == 409
    assert "süresi doldu" in yanit.json()["detail"]
    assert eski.durum == DURUM_YANIT_YOK


def test_yanitlanmis_linke_tekrar_yanit_verilemez():
    yanit = istemci(SahteReferans(durum=DURUM_YANITLANDI)).post(
        "/dogrulama/referans-yaniti",
        json={"token": "token-123", "puan": 5},
    )
    assert yanit.status_code == 409


def test_gecersiz_token_404_doner():
    yanit = istemci(None).get("/dogrulama/referans/olmayan-token")
    assert yanit.status_code == 404


# --- Yanıt gönderildikten sonra dönen gövde ----------------------------------
# Eskiden kanıtın tam durumu dönüyordu: aynı çıktının BAŞKA referanslarının
# e-postası, puanı, yorumu ve yanıt token'ı. Bu uç nokta girişsiz, yani tek bir
# token'ı olan referans kişi diğerlerinin yerine de yanıt verebiliyordu.

from types import SimpleNamespace  # noqa: E402

from app.schemas.dogrulama import ReferansYanitiSonucu  # noqa: E402

DIGER_EMAIL = "diger-referans@ornek.com"
DIGER_TOKEN = "digerinin-gizli-tokeni-1234567890"


class SiraliOturum:
    """`scalar()` çağrılarına sırayla hazır cevap veren oturum taklidi.

    Referans yanıtında sıra: referans, çıktı, gencin hesap kimliği (bildirim
    için; None = hesapsız profil, bildirim atlanır).
    """

    def __init__(self, *sonuclar):
        self.sonuclar = list(sonuclar)

    async def scalar(self, *_args, **_kwargs):
        return self.sonuclar.pop(0)

    async def commit(self):
        pass


def _yanitlanan_ve_diger_referans():
    yanitlanan = SimpleNamespace(
        token="token-123",
        durum=DURUM_BEKLIYOR,
        olusturma_tarihi=dt.datetime.now(dt.UTC),
        yanit_metni=None,
        puan=None,
        somut_cikti_id=uuid.uuid4(),
    )
    diger = SimpleNamespace(
        token=DIGER_TOKEN,
        referans_email=DIGER_EMAIL,
        durum=DURUM_YANITLANDI,
        puan=2,
        yanit_metni="Katkısı sınırlıydı",
    )
    cikti = SimpleNamespace(
        id=yanitlanan.somut_cikti_id,
        baslik="Mahalle kütüphanesi ödünç takip sistemi",
        yetenek_karti_id=uuid.uuid4(),
        guven_skoru=None,
        referans_istekleri=[yanitlanan, diger],
    )
    return yanitlanan, cikti


def test_yanit_sonrasi_baska_referansin_bilgisi_donmez():
    yanitlanan, cikti = _yanitlanan_ve_diger_referans()
    app.dependency_overrides[get_session] = lambda: SiraliOturum(yanitlanan, cikti, None)

    yanit = TestClient(app).post(
        "/dogrulama/referans-yaniti", json={"token": "token-123", "puan": 5}
    )

    assert yanit.status_code == 200
    assert DIGER_EMAIL not in yanit.text
    assert DIGER_TOKEN not in yanit.text
    assert "Katkısı sınırlıydı" not in yanit.text
    assert yanit.json() == {
        "baslik": "Mahalle kütüphanesi ödünç takip sistemi",
        "durum": DURUM_YANITLANDI,
    }


def test_yanit_sonrasi_skor_yine_de_hesaplanir():
    """Gövde daraldı, hesap değişmedi: iki referansın ortalaması yazılır."""
    yanitlanan, cikti = _yanitlanan_ve_diger_referans()
    app.dependency_overrides[get_session] = lambda: SiraliOturum(yanitlanan, cikti, None)

    TestClient(app).post("/dogrulama/referans-yaniti", json={"token": "token-123", "puan": 5})

    # 5 -> 3, 2 -> 1 : ortalama 2
    assert cikti.guven_skoru.ucuncu_taraf_onayi == 2


def test_yanitin_zamani_kaydedilir():
    """İş kalemi sonradan değişirse eski yanıtı ayırt etmenin dayanağı."""
    yanitlanan, cikti = _yanitlanan_ve_diger_referans()
    app.dependency_overrides[get_session] = lambda: SiraliOturum(yanitlanan, cikti, None)
    once = dt.datetime.now(dt.UTC)

    TestClient(app).post("/dogrulama/referans-yaniti", json={"token": "token-123", "puan": 5})

    assert yanitlanan.yanit_tarihi >= once


def test_yanit_sonucu_semasi_yalnizca_baslik_ve_durum_tasir():
    assert set(ReferansYanitiSonucu.model_fields) == {"baslik", "durum"}
