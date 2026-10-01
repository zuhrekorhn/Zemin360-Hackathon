"""Referans isteğinin durum makinesi ve zaman aşımı (app/agents/dogrulama/referans_durumu.py,
app/servisler/dogrulama/referans.py)."""

import asyncio
import datetime as dt
from types import SimpleNamespace

import pytest

from app.agents.dogrulama import (
    DURUM_BEKLIYOR,
    DURUM_GERI_CEKILDI,
    DURUM_YANIT_YOK,
    DURUM_YANITLANDI,
    HATIRLATMA_GUN,
    OLAY_GERI_CEK,
    OLAY_YANIT,
    OLAY_ZAMAN_ASIMI,
    REFERANS_TIMEOUT_GUN,
    GecersizReferansGecisi,
    hatirlatma_zamani_mi,
    referans_gecisi,
    yanitlanabilir_mi,
)
from app.models.bildirim import TUR_REFERANS_YANIT_YOK
from app.servisler.dogrulama import referans as referans_servisi
from app.servisler.dogrulama import (
    referansi_geri_cek,
    zaman_asimini_isle,
    zaman_asimlarini_isle,
)

SIMDI = dt.datetime(2026, 10, 1, 12, tzinfo=dt.UTC)
ESKI = SIMDI - dt.timedelta(days=REFERANS_TIMEOUT_GUN)
YENI = SIMDI - dt.timedelta(days=1)


@pytest.mark.parametrize(
    ("durum", "olay", "hedef"),
    [
        (DURUM_BEKLIYOR, OLAY_YANIT, DURUM_YANITLANDI),
        (DURUM_BEKLIYOR, OLAY_ZAMAN_ASIMI, DURUM_YANIT_YOK),
    ],
)
def test_gecerli_gecisler(durum, olay, hedef):
    assert referans_gecisi(durum, olay) == hedef


@pytest.mark.parametrize(
    ("durum", "olay", "cumle"),
    [
        (DURUM_YANITLANDI, OLAY_YANIT, "Bu referans zaten yanıtlanmış"),
        (DURUM_YANIT_YOK, OLAY_YANIT, "Bu referans isteğinin süresi doldu, yanıt alınamıyor."),
        (DURUM_YANITLANDI, OLAY_ZAMAN_ASIMI, "Bu referans isteği artık bu işlemi kabul etmiyor."),
    ],
)
def test_gecersiz_gecis_kullaniciya_dogru_cumleyi_soyler(durum, olay, cumle):
    with pytest.raises(GecersizReferansGecisi, match=cumle):
        referans_gecisi(durum, olay)


@pytest.mark.parametrize(
    ("durum", "yanitlanabilir"),
    [(DURUM_BEKLIYOR, True), (DURUM_YANITLANDI, False), (DURUM_YANIT_YOK, False)],
)
def test_yalnizca_bekleyen_istek_yanitlanabilir(durum, yanitlanabilir):
    assert yanitlanabilir_mi(durum) is yanitlanabilir


def _istek(durum: str, olusturma: dt.datetime) -> SimpleNamespace:
    return SimpleNamespace(durum=durum, olusturma_tarihi=olusturma, somut_cikti_id=None)


@pytest.fixture
def bildirimler(monkeypatch):
    """Zaman aşımı gence bildirim yazar; DB'siz testte çağrılar kaydedilir."""
    kayit: list = []

    async def kaydet(_oturum, cikti_id, tur, metin):
        kayit.append(tur)

    monkeypatch.setattr(referans_servisi, "_gence_bildir", kaydet)
    return kayit


def test_suresi_dolan_istek_yanit_yoka_gecer_ve_gence_bildirilir(bildirimler):
    istek = _istek(DURUM_BEKLIYOR, ESKI)
    assert asyncio.run(zaman_asimini_isle(None, istek, SIMDI)) is True
    assert istek.durum == DURUM_YANIT_YOK
    assert bildirimler == [TUR_REFERANS_YANIT_YOK]


def test_suresi_dolmayan_ve_yanitlanmis_istek_degismez(bildirimler):
    bekleyen, yanitlanmis = _istek(DURUM_BEKLIYOR, YENI), _istek(DURUM_YANITLANDI, ESKI)
    assert asyncio.run(zaman_asimini_isle(None, bekleyen, SIMDI)) is False
    assert asyncio.run(zaman_asimini_isle(None, yanitlanmis, SIMDI)) is False
    assert (bekleyen.durum, yanitlanmis.durum) == (DURUM_BEKLIYOR, DURUM_YANITLANDI)
    assert bildirimler == []


def test_coklu_islemde_hicbir_istek_atlanmaz(bildirimler):
    ilk, ikinci = _istek(DURUM_BEKLIYOR, ESKI), _istek(DURUM_BEKLIYOR, ESKI)
    assert asyncio.run(zaman_asimlarini_isle(None, [ilk, ikinci], SIMDI)) is True
    assert ikinci.durum == DURUM_YANIT_YOK
    assert len(bildirimler) == 2


# --- Geri çekme ve hatırlatma (plan § 7) -------------------------------------------------


def test_bekleyen_istek_geri_cekilir_ve_form_kapanir():
    assert referans_gecisi(DURUM_BEKLIYOR, OLAY_GERI_CEK) == DURUM_GERI_CEKILDI
    assert yanitlanabilir_mi(DURUM_GERI_CEKILDI) is False
    with pytest.raises(GecersizReferansGecisi, match="geri çekildi"):
        referans_gecisi(DURUM_GERI_CEKILDI, OLAY_YANIT)


@pytest.mark.parametrize("durum", [DURUM_YANITLANDI, DURUM_YANIT_YOK])
def test_yanitlanmis_ya_da_suresi_dolmus_istek_geri_cekilemez(durum):
    with pytest.raises(GecersizReferansGecisi):
        referans_gecisi(durum, OLAY_GERI_CEK)


def test_geri_cekmenin_tekrari_yan_etkisiz(bildirimler):
    istek = _istek(DURUM_BEKLIYOR, YENI)
    asyncio.run(referansi_geri_cek(None, istek))
    asyncio.run(referansi_geri_cek(None, istek))
    assert istek.durum == DURUM_GERI_CEKILDI


@pytest.mark.parametrize(
    ("gun", "durum", "hatirlatildi", "beklenen"),
    [
        (HATIRLATMA_GUN - 1, DURUM_BEKLIYOR, False, False),  # erken
        (HATIRLATMA_GUN, DURUM_BEKLIYOR, False, True),
        (HATIRLATMA_GUN + 1, DURUM_BEKLIYOR, True, False),  # tek hatırlatma
        (REFERANS_TIMEOUT_GUN, DURUM_BEKLIYOR, False, False),  # süre doldu
        (HATIRLATMA_GUN, DURUM_YANITLANDI, False, False),
    ],
)
def test_hatirlatma_ucuncu_gunde_bir_kez(gun, durum, hatirlatildi, beklenen):
    olusturma = SIMDI - dt.timedelta(days=gun)
    hatirlatma = SIMDI if hatirlatildi else None
    assert hatirlatma_zamani_mi(olusturma, durum, hatirlatma, SIMDI) is beklenen
