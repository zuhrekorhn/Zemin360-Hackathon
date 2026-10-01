"""Karne ölçütleri (degerlendirme/olcutler.py)."""

import pytest

from degerlendirme.degerlendirici import Degerlendirme
from degerlendirme.olcutler import VakaSonucu, karne_hesapla, uyuyor_mu, yakin_mi, yanlis_uc_mu
from degerlendirme.vaka import Vaka


@pytest.mark.parametrize(
    ("beklenti", "deger", "uyar", "yakin"),
    [
        (2, 2, True, True),
        (2, 3, False, True),
        (2, 0, False, False),
        (None, None, True, True),
        (None, 0, False, False),  # "—" ile 0 aynı şey değil
        (0, None, False, False),  # değerlendirmemek 0'a yakın sayılmaz
        ([2, 3], 3, True, True),
        ([2, None], None, True, True),
        ([0, 1], 3, False, False),
        ([0, 1], 2, False, True),
    ],
)
def test_uyum_ve_yakinlik(beklenti, deger, uyar, yakin):
    assert uyuyor_mu(beklenti, deger) is uyar
    assert yakin_mi(beklenti, deger) is yakin


@pytest.mark.parametrize(
    ("beklenti", "deger", "yanlis"),
    [(2, 3, True), (3, 3, False), ([2, 3], 3, False), (None, 3, True), (2, 2, False)],
)
def test_yanlis_uc(beklenti, deger, yanlis):
    assert yanlis_uc_mu(beklenti, deger) is yanlis


def _vaka(kimlik: str, *, beklenen=None, onerilen=None, kotu_niyetli=False) -> Vaka:
    return Vaka.model_validate(
        {
            "id": kimlik,
            "alan": "yazilim",
            "amac": "test",
            "kotu_niyetli": kotu_niyetli,
            "iddia": {"baslik": "Bir çalışma"},
            "kimlik": {"ad": "Ad Soyad", "eposta": "a@ornek.com"},
            "beklenen": beklenen,
            "onerilen": onerilen,
            "etiketleyen": "zuhre" if beklenen else None,
        }
    )


ETIKET = {"kanit": 2, "sonuc": 2, "rol": 2, "referans": None}


def test_etiketsiz_vaka_resmi_karneye_girmez_taslakta_girer():
    sonuclar = [VakaSonucu(_vaka("v1", onerilen=ETIKET), Degerlendirme(2, 2, 2, None))]
    assert karne_hesapla("x", sonuclar, taslak=False).olculen_vaka == 0
    taslak = karne_hesapla("x", sonuclar, taslak=True)
    assert taslak.olculen_vaka == 1
    assert taslak.basliklar["kanit"].birebir == 1.0


def test_kotu_niyetli_vakada_yanlis_uc_ayri_sayilir():
    sonuclar = [
        VakaSonucu(
            _vaka("sahte", beklenen=ETIKET, kotu_niyetli=True), Degerlendirme(2, 3, 2, None)
        ),
        VakaSonucu(_vaka("durust", beklenen=ETIKET), Degerlendirme(3, 2, 2, None)),
    ]
    karne = karne_hesapla("x", sonuclar, taslak=False)
    assert karne.sahte_yanlis_uc == ["sahte:sonuc"]
    assert sorted(karne.yanlis_uc) == ["durust:kanit", "sahte:sonuc"]
    assert not karne.esikleri_geciyor_mu


def test_sonuc_uretemeyen_vaka_uyusmadi_sayilir():
    sonuclar = [VakaSonucu(_vaka("asili", beklenen=ETIKET), Degerlendirme(hata="zaman_asimi"))]
    karne = karne_hesapla("x", sonuclar, taslak=False)
    assert karne.hatalar == {"asili": "zaman_asimi"}
    # Beklenen "—" olan Referans bile uyuşmuş sayılmaz: sistem sonuç üretmedi.
    assert all(o.birebir == 0.0 for o in karne.basliklar.values())


def test_notta_dil_ihlali_karneye_yazilir():
    sonuclar = [
        VakaSonucu(
            _vaka("v", beklenen=ETIKET),
            Degerlendirme(2, 2, 2, None, not_metni="Rolünüzü açıkça yazmışsınız."),
        )
    ]
    karne = karne_hesapla("x", sonuclar, taslak=False)
    assert "v" in karne.not_ihlalleri


def test_her_sey_uyusunca_esikler_gecer():
    sonuclar = [VakaSonucu(_vaka("v", beklenen=ETIKET), Degerlendirme(2, 2, 2, None))]
    assert karne_hesapla("x", sonuclar, taslak=False).esikleri_geciyor_mu
