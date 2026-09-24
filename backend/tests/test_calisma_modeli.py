"""Çalışma modeli — konumdan ayrı bir alan.

Önce "Uzaktan / fark etmez" şehir listesine konmuştu; bu "İstanbul'da ama
hibrit" gibi çok sık bir durumu ifade edilemez kılıyordu. LinkedIn ve
Kariyer.net de ikisini ayrı tutuyor.
"""

from app.core.calisma_modeli import (
    ETIKETLER,
    HIBRIT,
    IS_YERINDE,
    MODELLER,
    UZAKTAN,
    gecerli_mi,
    sehir_eslesmeli_mi,
    temizle,
)


def test_uc_model_var():
    assert MODELLER == (IS_YERINDE, HIBRIT, UZAKTAN)


def test_etiketler_turkce_ve_platformlardaki_gibi():
    assert ETIKETLER[IS_YERINDE] == "İş yerinde"
    assert ETIKETLER[HIBRIT] == "Hibrit"
    assert ETIKETLER[UZAKTAN] == "Uzaktan"


def test_tanimsiz_deger_gecersiz():
    assert gecerli_mi("evden") is False
    assert gecerli_mi(None) is False
    assert gecerli_mi(UZAKTAN) is True


def test_temizle_bilinmeyeni_atar_sirayi_sabitler():
    assert temizle([UZAKTAN, "evden", IS_YERINDE]) == [IS_YERINDE, UZAKTAN]


def test_temizle_tekrarlari_siler():
    assert temizle([HIBRIT, HIBRIT]) == [HIBRIT]


def test_bos_secim_bos_liste():
    assert temizle(None) == []
    assert temizle([]) == []


def test_uzaktan_isteginde_sehir_filtresi_yok():
    """İş uzaktan yapılacaksa gencin hangi şehirde olduğu önemli değil."""
    assert sehir_eslesmeli_mi(UZAKTAN) is False


def test_is_yerinde_ve_hibritte_sehir_eslesmeli():
    assert sehir_eslesmeli_mi(IS_YERINDE) is True
    assert sehir_eslesmeli_mi(HIBRIT) is True


def test_model_belirtilmemisse_eski_davranis():
    """Kartta model yoksa şehir tercihi tek başına filtre olmaya devam eder."""
    assert sehir_eslesmeli_mi(None) is True
