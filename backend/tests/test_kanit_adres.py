"""Kanıt adresinin kimliği (app/core/kanit_okuma/adres.py) ve erişim durumları."""

import pytest

from app.core.kanit_okuma.adres import normal_url
from app.core.kanit_okuma.belge import ErisimDurumu


@pytest.mark.parametrize(
    "yazim",
    [
        "https://github.com/ornek/kutuphane",
        "github.com/ornek/kutuphane",
        "http://www.github.com/ornek/kutuphane/",
        "HTTPS://GitHub.com:443/ornek/kutuphane#readme",
        "https://github.com/ornek/kutuphane?utm_source=x&fbclid=abc",
        "  //github.com/ornek/kutuphane  ",
    ],
)
def test_ayni_sayfanin_yazimlari_tek_bicime_iner(yazim):
    assert normal_url(yazim) == "https://github.com/ornek/kutuphane"


def test_anlamli_parametre_korunur_ve_siralanir():
    assert normal_url("youtube.com/watch?v=abc&t=10") == "https://youtube.com/watch?t=10&v=abc"


def test_yol_buyuk_kucuk_harfe_duyarli():
    assert normal_url("ornek.com/Proje") != normal_url("ornek.com/proje")


def test_standart_disi_port_korunur():
    assert normal_url("http://ornek.com:8080/x") == "https://ornek.com:8080/x"


def test_bozuk_adres_hata_vermez():
    assert normal_url("http://[bozuk") == "http://[bozuk"


@pytest.mark.parametrize(
    ("durum", "okunamadi"),
    [
        (ErisimDurumu.ACIK, False),
        (ErisimDurumu.BULUNAMADI, False),  # "yok": Kanıt 0
        (ErisimDurumu.GUVENSIZ, False),
        (ErisimDurumu.GIRIS_GEREKLI, True),  # okunamadı: "—"
        (ErisimDurumu.ENGELLENDI, True),
        (ErisimDurumu.ICERIK_YOK, True),
        (ErisimDurumu.HATA, True),
    ],
)
def test_okunamayan_erisim_durumlari(durum, okunamadi):
    assert durum.okunamadi_mi is okunamadi
