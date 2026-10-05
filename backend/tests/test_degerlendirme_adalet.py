"""Adalet raporu (degerlendirme/adalet.py, plan § 10.2)."""

from degerlendirme.adalet import (
    SORUN_AZ_VAKA,
    SORUN_ORTALAMA_GERIDE,
    SORUN_UC_YOLU_YOK,
    adalet_hesapla,
)
from degerlendirme.degerlendirici import Degerlendirme
from degerlendirme.olcutler import VakaSonucu, karne_hesapla
from degerlendirme.rapor import markdown
from degerlendirme.vaka import Vaka


def _sonuc(kimlik, alan, kanit, *, beklenen_kanit=None, kotu_niyetli=False, hata=None):
    etiket = {"kanit": beklenen_kanit, "sonuc": 2, "rol": 2, "referans": None}
    vaka = Vaka.model_validate(
        {
            "id": kimlik,
            "alan": alan,
            "amac": "test",
            "kotu_niyetli": kotu_niyetli,
            "iddia": {"baslik": "Bir çalışma"},
            "kimlik": {"ad": "Ad Soyad", "eposta": "a@ornek.com"},
            "beklenen": etiket,
            "etiketleyen": "zuhre",
        }
    )
    return VakaSonucu(vaka, Degerlendirme(kanit, 2, 2, None, hata=hata))


def _alan(rapor, ad):
    return next(a for a in rapor.alanlar if a.alan == ad)


def test_tire_ortalamaya_girmez_ve_ayri_oran_olarak_gorunur():
    rapor = adalet_hesapla(
        [
            _sonuc("a1", "yazilim", 3, beklenen_kanit=3),
            _sonuc("a2", "yazilim", None, beklenen_kanit=None),
            _sonuc("a3", "yazilim", 1, beklenen_kanit=1),
        ],
        taslak=False,
    )
    yazilim = _alan(rapor, "yazilim")
    assert yazilim.ortalama == 2.0  # (3 + 1) / 2; "—" sayılmaz
    assert yazilim.tire_orani == 1 / 3
    assert yazilim.en_yuksek == 3
    assert yazilim.uc_yolu == ("a1",)
    assert not yazilim.sorunlar


def test_kotu_niyetli_vaka_adalete_girmez():
    rapor = adalet_hesapla(
        [
            _sonuc("durust", "tasarim", 2, beklenen_kanit=2),
            _sonuc("sahte", "tasarim", 3, beklenen_kanit=0, kotu_niyetli=True),
        ],
        taslak=False,
    )
    tasarim = _alan(rapor, "tasarim")
    assert tasarim.durust_vaka == 1
    assert tasarim.en_yuksek == 2


def test_uc_yolu_olmayan_alan_isaretlenir_ve_etiketin_tavani_gorunur():
    rapor = adalet_hesapla(
        [_sonuc(f"k{i}", "kamuya_kapali", 2, beklenen_kanit=3) for i in range(3)],
        taslak=False,
    )
    alan = _alan(rapor, "kamuya_kapali")
    assert SORUN_UC_YOLU_YOK in alan.sorunlar
    assert alan.ulasilabilir == 3  # etiket 3'e ulaşılabilir diyor, sistem ulaşamıyor
    assert alan in rapor.sorunlu_alanlar


def test_ortalamasi_genelden_cok_geride_alan_ve_az_vakali_alan():
    sonuclar = [_sonuc(f"y{i}", "yazilim", 3, beklenen_kanit=3) for i in range(3)]
    sonuclar += [_sonuc("g0", "gonulluluk", 3, beklenen_kanit=3)]  # yol var ama tek vaka
    sonuclar += [
        _sonuc("m0", "medya", 3, beklenen_kanit=3),
        _sonuc("m1", "medya", 0, beklenen_kanit=0),
        _sonuc("m2", "medya", 0, beklenen_kanit=0),
        _sonuc("m3", "medya", 0, beklenen_kanit=0),
    ]
    rapor = adalet_hesapla(sonuclar, taslak=False)
    assert SORUN_ORTALAMA_GERIDE in _alan(rapor, "medya").sorunlar
    assert _alan(rapor, "gonulluluk").sorunlar == (SORUN_AZ_VAKA,)
    assert not _alan(rapor, "yazilim").sorunlar


def test_sonuc_uretemeyen_vaka_tire_gibi_sayilir_ortalamaya_girmez():
    rapor = adalet_hesapla(
        [
            _sonuc("a1", "veri", 3, beklenen_kanit=3),
            _sonuc("a2", "veri", None, beklenen_kanit=3, hata="zaman_asimi"),
        ],
        taslak=False,
    )
    veri = _alan(rapor, "veri")
    assert veri.ortalama == 3.0
    assert veri.tire_orani == 0.5


def test_karne_raporunda_adalet_bolumu_var():
    sonuclar = [_sonuc("a1", "yazilim", 3, beklenen_kanit=3)]
    metin = markdown(karne_hesapla("x", sonuclar, taslak=False), "2026-10-05")
    assert "## Adalet" in metin
    assert "| yazilim | 1 | 3.00 | 3 | 3 | %0 | a1 |" in metin
