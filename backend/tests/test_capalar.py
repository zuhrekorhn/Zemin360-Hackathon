"""Dosya çapaları (plan § 4.2, § 6.3): seviye kuralı, QR okuma, doğrulama adresi ayıklama,
bilinen düzenleyen ve adres doğrulayıcısı."""

import asyncio
import io

import httpx
import pytest
from PIL import Image

from app.agents.dogrulama.capalar import (
    TUR_ADRES,
    TUR_EDEVLET,
    TUR_IMZA,
    TUR_ROZET,
    KimlikDurumu,
    dosya_seviyesi,
)
from app.core.capalar.duzenleyenler import duzenleyen
from app.core.capalar.kodlar import dogrulama_adresleri, kodlari_oku
from app.core.kanit_okuma.belge import KaynakSeviyesi as S
from app.core.kanit_okuma.belge import SahiplikKaynagi
from app.servisler.dogrulama.capalar import CapaGirdisi, capalari_dogrula

TAM = KimlikDurumu(eposta_dogrulandi=True, ad_kilitli=True)
YOK = KimlikDurumu()


def seviye(capa, kimlik=TAM):
    return dosya_seviyesi({"capalar": [capa]}, kimlik).seviye


# --- Kural --------------------------------------------------------------------------------

ADRES = {"tur": TUR_ADRES, "okundu": True, "duzenleyen": "Credly"}
IMZA = {"tur": TUR_IMZA, "gecerli": True, "butun": True}


@pytest.mark.parametrize(
    ("capa", "kimlik", "beklenen"),
    [
        ({**ADRES, "ad_eslesti": True}, TAM, S.DUZENLEYEN),
        ({**ADRES, "ad_eslesti": True}, KimlikDurumu(eposta_dogrulandi=True), S.KAMUYA_ACIK),
        ({**ADRES, "ad_eslesti": True}, YOK, S.KAMUYA_ACIK),
        # E-posta eşleşmesi daha güçlü: adın kilitli olması gerekmez (§ 6.3)
        ({**ADRES, "eposta_eslesti": True}, KimlikDurumu(eposta_dogrulandi=True), S.DUZENLEYEN),
        ({**ADRES, "duzenleyen": None, "ad_eslesti": True}, TAM, S.KAMUYA_ACIK),
        ({**ADRES, "okundu": False, "ad_eslesti": True}, TAM, S.BEYAN),
    ],
)
def test_adres_capasi(capa, kimlik, beklenen):
    assert seviye(capa, kimlik) is beklenen


@pytest.mark.parametrize(
    ("capa", "beklenen"),
    [
        ({"tur": TUR_IMZA, "gecerli": True, "butun": True, "guvenilir": True}, S.KAMUYA_ACIK),
        (
            {
                "tur": TUR_IMZA,
                "gecerli": True,
                "butun": True,
                "guvenilir": True,
                "ad_eslesti": True,
            },
            S.DUZENLEYEN,
        ),
        ({"tur": TUR_IMZA, "gecerli": True, "butun": True, "ad_eslesti": True}, S.KAMUYA_ACIK),
        ({"tur": TUR_IMZA, "gecerli": True, "butun": False, "guvenilir": True}, S.BEYAN),
        ({"tur": TUR_ROZET, "dogrulandi": True, "eposta_eslesti": True}, S.DUZENLEYEN),
        (
            {"tur": TUR_ROZET, "dogrulandi": True, "eposta_eslesti": True, "iptal": True},
            S.BEYAN,
        ),
        ({"tur": TUR_ROZET, "dogrulandi": True, "alici_eposta_ile": True}, S.BEYAN),
        ({"tur": TUR_ROZET, "dogrulandi": True}, S.KAMUYA_ACIK),
        ({"tur": TUR_EDEVLET, "girvak_karari": None}, S.BEYAN),
        ({"tur": TUR_EDEVLET, "girvak_karari": "onaylandi"}, S.DUZENLEYEN),
        ({"tur": "bilinmeyen"}, S.BEYAN),
    ],
)
def test_diger_capalar(capa, beklenen):
    assert seviye(capa) is beklenen


def test_en_guclu_capa_ve_sahiplik_kaynagi():
    sonuc = dosya_seviyesi(
        {
            "capalar": [
                {**ADRES, "duzenleyen": None},
                {"tur": TUR_ROZET, "dogrulandi": True, "eposta_eslesti": True},
            ]
        },
        TAM,
    )
    assert sonuc.seviye is S.DUZENLEYEN
    assert sonuc.sahiplik is SahiplikKaynagi.EPOSTA
    assert dosya_seviyesi({}).seviye is S.BEYAN


# --- QR, adres ayıklama, düzenleyen -------------------------------------------------------


def _qr_png(metin: str) -> bytes:
    import zxingcpp

    matris = zxingcpp.create_barcode(metin, zxingcpp.BarcodeFormat.QRCode)
    gorsel = Image.fromarray(matris.to_image(scale=8)).convert("RGB")
    cikti = io.BytesIO()
    gorsel.save(cikti, format="PNG")
    return cikti.getvalue()


def test_qr_gorselden_okunur():
    bilgi = kodlari_oku(_qr_png("https://www.credly.com/badges/abc-123"), "image/png")
    assert bilgi["liste"][0]["metin"] == "https://www.credly.com/badges/abc-123"
    assert kodlari_oku(_qr_png_bos(), "image/png") is None


def _qr_png_bos() -> bytes:
    cikti = io.BytesIO()
    Image.new("RGB", (40, 40), "white").save(cikti, format="PNG")
    return cikti.getvalue()


def test_qr_pdf_sayfasindan_okunur():
    import pikepdf

    gorsel = Image.open(io.BytesIO(_qr_png("https://btkakademi.gov.tr/dogrula/XYZ")))
    pdf_akis = io.BytesIO()
    gorsel.save(pdf_akis, format="PDF")
    ham = pdf_akis.getvalue()
    assert pikepdf.open(io.BytesIO(ham))  # geçerli PDF
    bilgi = kodlari_oku(ham, "application/pdf")
    assert bilgi["liste"][0]["metin"] == "https://btkakademi.gov.tr/dogrula/XYZ"


def test_dogrulama_adresleri_kod_once_metinde_yalnizca_ipuclu_ya_da_bilinen():
    kodlar = [{"bicim": "QRCode", "metin": "https://ornek.org/verify/1"}]
    metin = (
        "Ayrıntı: https://blog.ornek.com/yazi ve doğrulama https://coursera.org/verify/ABC. "
        "Aynısı: https://www.ornek.org/verify/1/ ayrıca https://kurum.org/sertifika/9"
    )
    assert dogrulama_adresleri(kodlar, metin) == [
        "https://ornek.org/verify/1",
        "https://coursera.org/verify/ABC",
        "https://kurum.org/sertifika/9",
    ]


@pytest.mark.parametrize(
    ("adres", "beklenen"),
    [
        ("https://www.credly.com/badges/1", "Credly"),
        ("https://learn.microsoft.com/tr-tr/users/x/credentials/1", "Microsoft Learn"),
        ("https://credly.com.saldirgan.io/badges/1", None),
        ("https://notcredly.com/badges/1", None),
        ("bozuk adres", None),
    ],
)
def test_bilinen_duzenleyen(adres, beklenen):
    assert duzenleyen(adres) == beklenen


# --- Adres doğrulayıcısı ------------------------------------------------------------------


def _girdi(metin="", kodlar=(), isleyici=None, **ek):
    return CapaGirdisi(
        ham=b"",
        icerik_turu="application/pdf",
        metin=metin,
        on_bilgi={"kodlar": {"liste": list(kodlar)}} if kodlar else {},
        ad="Elif Yılmaz",
        eposta="elif@ornek.com",
        transport=httpx.MockTransport(isleyici) if isleyici else None,
        **ek,
    )


def test_adres_dogrulayici_sayfada_adi_ve_duzenleyeni_kaydeder(monkeypatch):
    import ipaddress

    from app.core import guvenli_istek

    async def coz(host, port):
        return [ipaddress.ip_address("93.184.216.34")]

    monkeypatch.setattr(guvenli_istek, "cozumleyici", coz)

    def isleyici(request):
        return httpx.Response(
            200,
            html=(
                "<html><head><title>Python Temelleri Sertifikası</title></head>"
                "<body><h1>ELİF YILMAZ</h1><p>Bu belge Coursera tarafından verilmiştir.</p>"
                "</body></html>"
            ),
            headers={"content-type": "text/html"},
        )

    kodlar = [{"bicim": "QRCode", "metin": "https://coursera.org/verify/ABC"}]
    bulgular = asyncio.run(capalari_dogrula(_girdi(kodlar=kodlar, isleyici=isleyici)))
    [bulgu] = bulgular
    assert bulgu["tur"] == TUR_ADRES
    assert bulgu["kaynak"] == "kod"
    assert bulgu["duzenleyen"] == "Coursera"
    assert bulgu["okundu"] is True
    assert bulgu["ad_eslesti"] is True
    assert bulgu["eposta_eslesti"] is False
    assert seviye(bulgu) is S.DUZENLEYEN


def test_dogrulayici_hatasi_yuklemeyi_dusurmez(monkeypatch):
    from app.servisler.dogrulama import capalar

    class Bozuk:
        ad = "bozuk"

        async def dogrula(self, girdi):
            raise RuntimeError("ağ yok")

    monkeypatch.setattr(capalar, "DOGRULAYICILAR", [Bozuk()])
    assert asyncio.run(capalari_dogrula(_girdi())) == []
