"""İlan düzenleme kuralları (docs/kararlar.md D1 § Kurallar). LLM/DB yok."""

import pytest

from app.agents.ihtiyac_duzenleme import (
    ILAN_KAPALI,
    ISBIRLIGI_BASLADI,
    bildirim_alacak,
    degisen_alanlar,
    duzenlenebilir_mi,
    gerekcesi_sifirlanacak,
)


def test_acik_ilan_duzenlenebilir():
    assert duzenlenebilir_mi("acik", ["onerildi", "genc_ilgilendi", "reddedildi"]) is None


def test_kapali_ilan_duzenlenemez():
    assert duzenlenebilir_mi("kapandi", []) == ILAN_KAPALI


def test_is_birligi_baslayan_ilan_duzenlenemez():
    assert duzenlenebilir_mi("acik", ["onerildi", "kabul_edildi"]) == ISBIRLIGI_BASLADI


def test_degisen_alanlar_bosluk_ve_bos_metni_ayni_sayar():
    eski = {"problem_tanimi": "Stok takibi", "kisitlar": None, "calisma_modeli": ["uzaktan"]}
    yeni = {"problem_tanimi": " Stok takibi ", "kisitlar": "", "calisma_modeli": ("uzaktan",)}
    assert degisen_alanlar(eski, yeni) == set()


def test_degisen_alanlar_yalnizca_degisenleri_doner():
    eski = {"problem_tanimi": "A", "basari_olcutu": {"metrik": "x", "hedef": "10"}}
    yeni = {"problem_tanimi": "A", "basari_olcutu": {"metrik": "x", "hedef": "20"}}
    assert degisen_alanlar(eski, yeni) == {"basari_olcutu"}


@pytest.mark.parametrize(
    ("durum", "sifirlanir", "bildirim"),
    [
        ("onerildi", True, False),
        ("ilgileniliyor", True, True),
        ("genc_ilgilendi", False, True),
        ("kabul_edildi", False, False),
        ("reddedildi", False, False),
        ("kapandi", False, False),
    ],
)
def test_durum_tablosu(durum, sifirlanir, bildirim):
    assert gerekcesi_sifirlanacak(durum) is sifirlanir
    assert bildirim_alacak(durum) is bildirim
