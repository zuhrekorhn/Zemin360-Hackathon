"""Referans isteğinin durum makinesi ve zaman aşımı (app/agents/dogrulama/referans_durumu.py,
app/servisler/dogrulama/referans.py)."""

import datetime as dt
from types import SimpleNamespace

import pytest

from app.agents.dogrulama import (
    DURUM_BEKLIYOR,
    DURUM_YANIT_YOK,
    DURUM_YANITLANDI,
    OLAY_YANIT,
    OLAY_ZAMAN_ASIMI,
    REFERANS_TIMEOUT_GUN,
    GecersizReferansGecisi,
    referans_gecisi,
    yanitlanabilir_mi,
)
from app.servisler.dogrulama import zaman_asimini_isle, zaman_asimlarini_isle

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
    return SimpleNamespace(durum=durum, olusturma_tarihi=olusturma)


def test_suresi_dolan_istek_yanit_yoka_gecer():
    istek = _istek(DURUM_BEKLIYOR, ESKI)
    assert zaman_asimini_isle(istek, SIMDI) is True
    assert istek.durum == DURUM_YANIT_YOK


def test_suresi_dolmayan_ve_yanitlanmis_istek_degismez():
    bekleyen, yanitlanmis = _istek(DURUM_BEKLIYOR, YENI), _istek(DURUM_YANITLANDI, ESKI)
    assert zaman_asimini_isle(bekleyen, SIMDI) is False
    assert zaman_asimini_isle(yanitlanmis, SIMDI) is False
    assert (bekleyen.durum, yanitlanmis.durum) == (DURUM_BEKLIYOR, DURUM_YANITLANDI)


def test_coklu_islemde_hicbir_istek_atlanmaz():
    """İlk istek geçince `any` kısa devre yapıp ikinciyi atlamamalı."""
    ilk, ikinci = _istek(DURUM_BEKLIYOR, ESKI), _istek(DURUM_BEKLIYOR, ESKI)
    assert zaman_asimlarini_isle([ilk, ikinci], SIMDI) is True
    assert ikinci.durum == DURUM_YANIT_YOK
