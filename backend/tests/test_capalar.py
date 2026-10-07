"""Dosya çapaları (docs/dogrulama.md § 4.2, § 6.3): seviye kuralı, QR okuma, doğrulama adresi
ayıklama,
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


# --- E-imza ---------------------------------------------------------------------------------


def _imza_girdisi(ham, metin="Elif Yilmaz bu kursu tamamlamistir"):
    return CapaGirdisi(
        ham=ham, icerik_turu="application/pdf", metin=metin, ad="Elif Yılmaz", eposta="e@o.com"
    )


def test_imzali_pdf_guvenilir_kokle_duzenleyen(monkeypatch):
    from app.core.capalar import eimza
    from app.servisler.dogrulama.capalar.imza import ImzaDogrulayici
    from tests import dosya_ornekleri as ornek

    ham, sertifika = ornek.imzali_pdf(["Katilim Belgesi", "Elif Yilmaz"])
    monkeypatch.setattr(
        "app.servisler.dogrulama.capalar.imza.guvenilir_kokler", lambda _k: (sertifika,)
    )
    [bulgu] = asyncio.run(ImzaDogrulayici().dogrula(_imza_girdisi(ham)))
    assert bulgu["gecerli"] and bulgu["butun"] and bulgu["guvenilir"]
    assert bulgu["imzalayan"].endswith("Ornek Universitesi")
    assert bulgu["ad_eslesti"] is True and bulgu["imzalayan_genc"] is False
    assert seviye(bulgu) is S.DUZENLEYEN

    # Kök tanınmıyor: imza geçerli ve bütün ama C
    monkeypatch.setattr("app.servisler.dogrulama.capalar.imza.guvenilir_kokler", lambda _k: ())
    [tanınmayan] = asyncio.run(ImzaDogrulayici().dogrula(_imza_girdisi(ham)))
    assert tanınmayan["gecerli"] and not tanınmayan["guvenilir"]
    assert seviye(tanınmayan) is S.KAMUYA_ACIK
    assert len(eimza.guvenilir_kokler()) > 50  # certifi


def test_imzadan_sonra_degistirilen_pdf_beyan(monkeypatch):
    from app.servisler.dogrulama.capalar.imza import ImzaDogrulayici
    from tests import dosya_ornekleri as ornek

    ham, sertifika = ornek.imzali_pdf(["Katilim Belgesi", "Elif Yilmaz"])
    # İmzalı aralıktaki ilk akışın bir baytı değişir (belge imzadan sonra oynanmış).
    i = ham.index(b"stream") + 8
    bozuk = ham[:i] + bytes([ham[i] ^ 0x01]) + ham[i + 1 :]
    monkeypatch.setattr(
        "app.servisler.dogrulama.capalar.imza.guvenilir_kokler", lambda _k: (sertifika,)
    )
    [bulgu] = asyncio.run(ImzaDogrulayici().dogrula(_imza_girdisi(bozuk)))
    assert bulgu["gecerli"] is False
    assert seviye(bulgu) is S.BEYAN


def test_gencin_kendi_imzaladigi_belge_en_cok_kamuya_acik(monkeypatch):
    from app.servisler.dogrulama.capalar.imza import ImzaDogrulayici
    from tests import dosya_ornekleri as ornek

    ham, sertifika = ornek.imzali_pdf(["Rapor", "Elif Yilmaz"], imzalayan="Elif Yilmaz")
    monkeypatch.setattr(
        "app.servisler.dogrulama.capalar.imza.guvenilir_kokler", lambda _k: (sertifika,)
    )
    [bulgu] = asyncio.run(ImzaDogrulayici().dogrula(_imza_girdisi(ham)))
    assert bulgu["imzalayan_genc"] is True
    assert seviye(bulgu) is S.KAMUYA_ACIK


def test_imzasiz_pdf_imza_capasi_yok():
    from app.servisler.dogrulama.capalar.imza import ImzaDogrulayici
    from tests import dosya_ornekleri as ornek

    assert asyncio.run(ImzaDogrulayici().dogrula(_imza_girdisi(ornek.pdf()))) == []


# --- Open Badges ----------------------------------------------------------------------------

ROZET_ADRESI = "https://www.credly.com/api/v1/obi/v2/badge_assertions/abc"


def _alici(eposta="elif@ornek.com", tuz="tuz1"):
    import hashlib

    ozet = hashlib.sha256((eposta + tuz).encode()).hexdigest()
    return {"type": "email", "hashed": True, "salt": tuz, "identity": f"sha256${ozet}"}


def _rozet_png(veri: str) -> bytes:
    from PIL.PngImagePlugin import PngInfo

    bilgi = PngInfo()
    bilgi.add_itxt("openbadges", veri)
    cikti = io.BytesIO()
    Image.new("RGB", (16, 16), "blue").save(cikti, format="PNG", pnginfo=bilgi)
    return cikti.getvalue()


def _rozet_girdisi(veri, sunulan, eposta="elif@ornek.com", monkeypatch=None):
    import ipaddress
    import json

    from app.core import guvenli_istek

    async def coz(host, port):
        return [ipaddress.ip_address("93.184.216.34")]

    monkeypatch.setattr(guvenli_istek, "cozumleyici", coz)

    def isleyici(istek):
        if sunulan is None:
            return httpx.Response(404)
        return httpx.Response(200, content=json.dumps(sunulan).encode())

    from app.core.capalar.rozet import rozet_verisini_oku

    return CapaGirdisi(
        ham=b"",
        icerik_turu="image/png",
        metin="",
        on_bilgi={"rozet": rozet_verisini_oku(_rozet_png(veri), "image/png")},
        ad="Elif Yılmaz",
        eposta=eposta,
        transport=httpx.MockTransport(isleyici),
    )


def _rozet_dogrula(girdi):
    from app.servisler.dogrulama.capalar.rozet import RozetDogrulayici

    return asyncio.run(RozetDogrulayici().dogrula(girdi))


def test_rozet_verisi_yeniden_kodlamadan_once_okunur():
    import json

    from app.core.dosya_hatti import gorsel_temizle

    png = _rozet_png(json.dumps({"id": ROZET_ADRESI}))
    from app.core.capalar.rozet import rozet_verisini_oku

    assert ROZET_ADRESI in rozet_verisini_oku(png, "image/png")["veri"]
    temiz, _ = gorsel_temizle(png, "image/png")
    assert rozet_verisini_oku(temiz, "image/png") is None


def test_barindirilan_rozet_alici_eposta_eslesirse_duzenleyen(monkeypatch):
    import json

    iddia = {"id": ROZET_ADRESI, "recipient": _alici(), "verification": {"type": "hosted"}}
    sunulan = {**iddia, "badge": {"name": "AWS Cloud Practitioner"}}
    [bulgu] = _rozet_dogrula(_rozet_girdisi(json.dumps(iddia), sunulan, monkeypatch=monkeypatch))
    assert bulgu["dogrulandi"] and bulgu["eposta_eslesti"] and not bulgu["iptal"]
    assert bulgu["duzenleyen"] == "Credly" and bulgu["rozet_adi"] == "AWS Cloud Practitioner"
    assert seviye(bulgu) is S.DUZENLEYEN


def test_baskasinin_rozeti_ve_iptal_edilmis_rozet_beyan(monkeypatch):
    import json

    iddia = {"id": ROZET_ADRESI, "recipient": _alici("baska@ornek.com")}
    [bulgu] = _rozet_dogrula(_rozet_girdisi(json.dumps(iddia), iddia, monkeypatch=monkeypatch))
    assert bulgu["dogrulandi"] and not bulgu["eposta_eslesti"]
    assert seviye(bulgu) is S.BEYAN

    iptal = {**iddia, "recipient": _alici(), "revoked": True}
    [bulgu] = _rozet_dogrula(_rozet_girdisi(json.dumps(iptal), iptal, monkeypatch=monkeypatch))
    assert seviye(bulgu) is S.BEYAN


def test_sunulan_iddia_farkliysa_dogrulanmaz(monkeypatch):
    import json

    iddia = {"id": ROZET_ADRESI, "recipient": _alici()}
    sunulan = {"id": ROZET_ADRESI, "recipient": _alici("baska@ornek.com")}
    [bulgu] = _rozet_dogrula(_rozet_girdisi(json.dumps(iddia), sunulan, monkeypatch=monkeypatch))
    assert bulgu["dogrulandi"] is False
    [yok] = _rozet_dogrula(_rozet_girdisi(json.dumps(iddia), None, monkeypatch=monkeypatch))
    assert yok["dogrulandi"] is False


def test_imzali_rozet_dogrulanmaz(monkeypatch):
    [bulgu] = _rozet_dogrula(
        _rozet_girdisi("eyJhbGciOiJSUzI1NiJ9.eyJ9.c2ln", None, monkeypatch=monkeypatch)
    )
    assert bulgu["bicim"] == "imzali" and seviye(bulgu) is S.BEYAN


@pytest.mark.parametrize(
    ("alici", "beklenen"),
    [
        (_alici(), (True, True)),
        ({"type": "email", "hashed": False, "identity": "Elif@Ornek.com"}, (True, True)),
        ({"type": "url", "identity": "https://elif.dev"}, (False, False)),
        ("elif@ornek.com", (True, True)),
    ],
)
def test_alici_eslesmesi(alici, beklenen):
    from app.core.capalar.rozet import alici_eslesir

    assert alici_eslesir(alici, "elif@ornek.com") == beklenen


# --- e-Devlet -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("metin", "beklenen"),
    [
        ("e-Devlet Kapısı ... Barkod No: ABCD-1234-EFGH-5678", "ABCD-1234-EFGH-5678"),
        ("TÜRKİYE.GOV.TR belge doğrulama BARKOD : 12AB34CD56 ile", "12AB34CD56"),
        ("Barkod No: ABCD-1234-EFGH-5678", None),  # e-Devlet ipucu yok
        ("e-Devlet barkod: kısa1", None),
        ("e-Devlet belgesi, barkod yok", None),
    ],
)
def test_edevlet_barkodu(metin, beklenen):
    from app.core.capalar.edevlet import edevlet_barkodu

    assert edevlet_barkodu(metin) == beklenen


# --- C2PA -----------------------------------------------------------------------------------


def test_c2pa_yoksa_sonuc_cikarilmaz():
    from app.core.capalar.c2pa_okuma import c2pa_oku
    from tests import dosya_ornekleri as ornek

    assert c2pa_oku(ornek.gorsel("PNG"), "image/png") is None
    assert c2pa_oku(ornek.gorsel("JPEG"), "image/jpeg") is None


def test_c2pa_ozeti_arac_ve_eylemler():
    from app.core.capalar.c2pa_okuma import c2pa_ozeti

    depo = {
        "active_manifest": "urn:1",
        "manifests": {
            "urn:1": {
                "claim_generator": "Adobe_Photoshop/25.0",
                "assertions": [
                    {
                        "label": "c2pa.actions.v2",
                        "data": {
                            "actions": [
                                {"action": "c2pa.created"},
                                {"action": "c2pa.edited"},
                                {"action": "c2pa.edited"},
                            ]
                        },
                    }
                ],
                "signature_info": {"issuer": "Adobe Inc."},
            }
        },
    }
    assert c2pa_ozeti(depo) == {
        "arac": "Adobe_Photoshop/25.0",
        "eylemler": ["created", "edited"],
        "imzalayan": "Adobe Inc.",
        "gecerli": True,
    }
    assert c2pa_ozeti({"manifests": {}}) is None
