"""Dosya içeriğinin okunması (plan § 4.3): metin katmanı, model okuması, maskeleme,
değerlendirme girdisi ve görselde alıntı kaynağı."""

import asyncio

import pytest

from app.agents.dogrulama.capalar import dosya_seviyesi
from app.agents.dogrulama.cekirdek import DegerlendirmeGirdisi, kalemi_degerlendir
from app.agents.dogrulama.cikarim import KanitCikarimi
from app.agents.dogrulama.dosya_cikarimi import DosyaOkunusu
from app.agents.dogrulama.okuma import dosya_okunusu
from app.core.dis_servisler.virus import KapaliTarayici
from app.core.dosya_hatti import dosyayi_hazirla
from app.core.kanit_okuma.belge import ErisimDurumu, KaynakSeviyesi
from app.core.kanit_okuma.maskeleme import maskele, tc_kimlik_gecerli_mi
from app.core.kanit_okuma.pdf import model_okumali_mi, pdf_metni
from app.servisler.dogrulama.dosyalar import icerigi_oku
from tests import dosya_ornekleri as ornek

SATIRLAR = [
    "Kopru Analiz Raporu",
    "Hazirlayan: Elif Yilmaz, ODTU Insaat Muhendisligi",
    "Bu raporda kopru tasiyici sisteminin sonlu elemanlar analizi yapilmistir.",
    "Iletisim: 0532 123 45 67",
]


async def _gom(metinler, _tur):
    return [[1.0, 0.0] for _ in metinler]


def test_tc_kimlik_saglamasi():
    assert tc_kimlik_gecerli_mi("10000000146")
    assert not tc_kimlik_gecerli_mi("10000000147")
    assert not tc_kimlik_gecerli_mi("01234567890")


@pytest.mark.parametrize(
    ("metin", "beklenen"),
    [
        ("T.C. Kimlik No: 10000000146", "T.C. Kimlik No: [T.C. kimlik no]"),
        ("Öğrenci no 12345678901", "Öğrenci no 12345678901"),  # sağlama tutmuyor
        ("Tel: 0532 123 45 67", "Tel: [telefon]"),
        ("+90 (532) 123-45-67 arayın", "[telefon] arayın"),
        ("Ödül: 12.500 TL", "Ödül: 12.500 TL"),
        (
            "Adres: Kızılay Mahallesi Atatürk Bulvarı No: 12 D: 4 Çankaya",
            "Adres: [adres] Çankaya",
        ),
    ],
)
def test_maskele(metin, beklenen):
    assert maskele(metin) == beklenen


def test_metin_katmani_okunur_model_cagrilmaz(dosya_modele_okutulmaz):
    ham = ornek.metinli_pdf(SATIRLAR * 3)
    metin, sayfa = pdf_metni(ham)
    assert "sonlu elemanlar" in metin and sayfa == 1
    assert not model_okumali_mi(metin, sayfa)

    icerik = asyncio.run(icerigi_oku(asyncio.run(dosyayi_hazirla(ham, KapaliTarayici()))))
    assert icerik.okuyan == "metin_katmani"
    assert "[telefon]" in icerik.tam_metin and "0532" not in icerik.tam_metin
    assert dosya_modele_okutulmaz["cagrilar"] == []


def test_taranmis_pdf_ve_gorsel_modele_okutulur(dosya_modele_okutulmaz):
    dosya_modele_okutulmaz["deger"] = DosyaOkunusu(
        gorsel_metni="Katılım Belgesi  Elif Yılmaz  Tel 0532 123 45 67",
        betim="Bir katılım belgesi",
    )
    for ham in (ornek.pdf(), ornek.gorsel("PNG")):
        hazir = asyncio.run(dosyayi_hazirla(ham, KapaliTarayici()))
        icerik = asyncio.run(icerigi_oku(hazir))
        assert icerik.okuyan == "model"
        assert icerik.betim == "Bir katılım belgesi"
        assert icerik.tam_metin == icerik.gorsel_metni
        assert "[telefon]" in icerik.tam_metin
    assert dosya_modele_okutulmaz["cagrilar"] == ["application/pdf", "image/png"]


def test_dosya_okunusu_betim_baglam_alinti_yalnizca_yazili_metin():
    okunan = asyncio.run(
        dosya_okunusu(
            tur="gorsel",
            dosya_adi="masa.jpg",
            tam_metin="",
            betim="Ahşaptan yapılmış bir masa",
            seviye=KaynakSeviyesi.BEYAN,
            iddia_sorgulari=["Masa"],
            gom=_gom,
        )
    )
    assert okunan.erisim is ErisimDurumu.ACIK
    assert "Ahşaptan" in okunan.metin
    assert okunan.alinti_metni == ""
    bos = asyncio.run(
        dosya_okunusu(
            tur="dosya",
            dosya_adi="x.pdf",
            tam_metin=None,
            betim=None,
            seviye=KaynakSeviyesi.BEYAN,
            iddia_sorgulari=[],
            gom=_gom,
        )
    )
    assert bos.erisim is ErisimDurumu.ICERIK_YOK


def test_capasiz_gorsel_kanit_1_betimden_alinti_sayilmaz():
    """Fotoğraftaki iş ilgiliyse Kanıt 1 (çapasız dosya, § 2); betimden alıntılanan
    yetenek kabul edilmez, çünkü betimi model yazdı."""
    okunan = asyncio.run(
        dosya_okunusu(
            tur="gorsel",
            dosya_adi="masa.jpg",
            tam_metin="",
            betim="Ahşaptan yapılmış bir masa",
            seviye=dosya_seviyesi({}),
            iddia_sorgulari=["Masa"],
            gom=_gom,
        )
    )

    async def cikar(alanlar):
        assert alanlar["kanit_adresi"] == "yüklenen dosya: masa.jpg"
        return KanitCikarimi(
            ilgili_mi=True,
            sonuc_var=False,
            sonuc_sayisal=False,
            sonuc_olcut_acik=False,
            pay_var=True,
            pay_ozgul=True,
            kanitlanan_yetenekler=[{"yetenek": "Ahşap", "alinti": "Ahşaptan yapılmış bir masa"}],
        )

    girdi = DegerlendirmeGirdisi(baslik="Masa", yetenekler=("Ahşap",))
    sonuc = asyncio.run(kalemi_degerlendir(girdi, [okunan], cikar))
    assert sonuc.puanlar.kanit == 1
    assert sonuc.yetenek_kanitlari == ()
    assert "doğrulanabilir bir işaret" in sonuc.not_metni


@pytest.mark.parametrize(
    ("capalar", "beklenen"),
    [
        ([], KaynakSeviyesi.BEYAN),
        ([{"tur": "qr", "sonuc": "gecersiz"}], KaynakSeviyesi.BEYAN),
        ([{"tur": "edevlet", "sonuc": "incelemede"}], KaynakSeviyesi.BEYAN),
        ([{"tur": "qr", "sonuc": "kamuya_acik"}], KaynakSeviyesi.KAMUYA_ACIK),
        (
            [{"tur": "qr", "sonuc": "kamuya_acik"}, {"tur": "imza", "sonuc": "dogrulandi"}],
            KaynakSeviyesi.DUZENLEYEN,
        ),
    ],
)
def test_dosya_seviyesi_en_guclu_capa(capalar, beklenen):
    assert dosya_seviyesi({"capalar": capalar}) is beklenen
