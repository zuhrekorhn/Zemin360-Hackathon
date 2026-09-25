"""Müsaitlik kod olarak saklanır; okuma hoşgörülü, istek katı.

Gerçek risk: Tanımlama Ajanı "tam zamanlı" yazınca eşleştirmenin düz eşitlik
filtresi gencin `tam_zamanli` koduyla eşleşmiyor, tüm adaylar skor
hesaplanmadan eleniyordu (şehirde yaşanan hatanın aynısı).
"""

import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.agents.tanimlama import IhtiyacCikarimi
from app.core.musaitlik import (
    MUSAITLIKLER,
    PROJE_BAZLI,
    STAJ,
    TAM_ZAMANLI,
    YARIM_ZAMANLI,
    musaitlik_dogrula,
    musaitlik_kanonik,
)
from app.db.session import get_session
from app.main import app
from app.schemas.tanimlama import IhtiyacTaslagi, IhtiyacTaslagiGirdisi
from tests.sahte_hesap import giris_yapmis, sahte_hesap, sohbet_degerleri

KURUM = sahte_hesap("kurum")
GENC = sahte_hesap("genc")

# --- Kanonikleştirme ----------------------------------------------------------


@pytest.mark.parametrize(
    ("girdi", "beklenen"),
    [
        ("tam_zamanli", TAM_ZAMANLI),
        ("Tam zamanlı", TAM_ZAMANLI),
        ("TAM ZAMANLI", TAM_ZAMANLI),
        ("tam-zamanli", TAM_ZAMANLI),
        ("yarı zamanlı", YARIM_ZAMANLI),
        ("part time", YARIM_ZAMANLI),
        ("Proje bazlı", PROJE_BAZLI),
        ("freelance", PROJE_BAZLI),
        ("Staj", STAJ),
    ],
)
def test_yazim_varyantlari_koda_cevrilir(girdi, beklenen):
    assert musaitlik_kanonik(girdi) == beklenen


def test_hosgorulu_okuma_tanimayani_none_yapar():
    assert musaitlik_kanonik("hafta sonları") is None
    assert musaitlik_kanonik("") is None
    assert musaitlik_kanonik(None) is None


def test_kati_okuma_tanimayani_reddeder():
    with pytest.raises(ValueError, match="Tanınmayan müsaitlik"):
        musaitlik_dogrula("hafta sonları")
    # Boş değer "tercih yok" demek, hata değil
    assert musaitlik_dogrula("") is None
    assert musaitlik_dogrula(None) is None


def test_llm_cikarimi_yalnizca_kod_kabul_eder():
    """Ajan serbest metin yazamasın; sessiz eleme buradan başlıyordu."""
    assert IhtiyacCikarimi(musaitlik_tercihi=TAM_ZAMANLI).musaitlik_tercihi == TAM_ZAMANLI
    with pytest.raises(ValidationError):
        IhtiyacCikarimi(musaitlik_tercihi="tam zamanlı gibi bir şey")


def test_dort_kod_var():
    assert MUSAITLIKLER == (TAM_ZAMANLI, YARIM_ZAMANLI, PROJE_BAZLI, STAJ)


# --- Okuma (checkpoint) ile istek (onay) ayrımı --------------------------------


def test_checkpoint_taslagi_hosgorulu_okunur():
    """Eski serbest metin taslağı kırmaz: bilineni koda çevirir, gerisini atar."""
    assert IhtiyacTaslagi(musaitlik_tercihi="Tam zamanlı").musaitlik_tercihi == TAM_ZAMANLI
    assert IhtiyacTaslagi(musaitlik_tercihi="tam zamanlı gibi bir şey").musaitlik_tercihi is None


def test_onay_girdisi_kati_okunur():
    assert IhtiyacTaslagiGirdisi(musaitlik_tercihi="staj").musaitlik_tercihi == STAJ
    with pytest.raises(ValidationError):
        IhtiyacTaslagiGirdisi(musaitlik_tercihi="haftasonu")


class EskiTaslakliGrafik:
    """Checkpoint'te müsaitliği serbest metin olarak duran eski bir sohbet."""

    TASLAK = {
        "problem_tanimi": "Destek biletleri elle ayrılıyor",
        "basari_kriteri": None,
        "musaitlik_tercihi": "tam zamanlı gibi bir şey",
    }

    async def aget_state(self, _config):
        return SimpleNamespace(
            values=sohbet_degerleri(KURUM, taslak_hazir=False, taslak=self.TASLAK)
        )

    async def ainvoke(self, _girdi, config=None):
        return {"taslak": self.TASLAK, "sonraki_soru": "Neye bakıp oldu diyeceksiniz?"}


def test_eski_taslakla_sohbet_ucu_kirilmaz():
    app.state.tanimlama_grafigi = EskiTaslakliGrafik()
    try:
        with giris_yapmis(KURUM):
            yanit = TestClient(app).post(
                "/tanimlama/sohbet/cevap",
                json={"oturum_id": str(uuid.uuid4()), "cevap": "Ayda 3000 bilet geliyor"},
            )
    finally:
        del app.state.tanimlama_grafigi

    assert yanit.status_code == 200
    assert yanit.json()["taslak"]["musaitlik_tercihi"] is None


@pytest.fixture
def oturumsuz():
    """Doğrulama hatası handler'a varmadan döner; oturum hiç kullanılmamalı."""
    app.dependency_overrides[get_session] = lambda: None
    yield
    app.dependency_overrides.clear()


def test_gecersiz_musaitlikle_ihtiyac_onayi_422(oturumsuz):
    with giris_yapmis(KURUM):
        yanit = _onayla_kurum()
    assert yanit.status_code == 422
    assert "haftasonu" in yanit.text


def _onayla_kurum():
    return TestClient(app).post(
        "/tanimlama/kart/onayla",
        json={
            "oturum_id": str(uuid.uuid4()),
            "kurum_profili": {},
            "duzeltilmis_taslak": {
                "problem_tanimi": "Destek biletleri elle ayrılıyor",
                "musaitlik_tercihi": "haftasonu",
            },
        },
    )


def test_gecersiz_musaitlikle_yetenek_onayi_422(oturumsuz):
    with giris_yapmis(GENC):
        yanit = _onayla_genc()
    assert yanit.status_code == 422


def _onayla_genc():
    return TestClient(app).post(
        "/kesif/kart/onayla",
        json={
            "oturum_id": str(uuid.uuid4()),
            "profil": {"sehir": "İstanbul", "musaitlik": "haftasonu"},
        },
    )
