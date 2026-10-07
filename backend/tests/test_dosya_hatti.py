"""Yükleme hattı (docs/dogrulama.md § 4.4): tür, boyut, virüs, ön okuma, temizlik."""

import asyncio
import io

import pikepdf
import pytest
from PIL import Image

from app.core import dosya_hatti
from app.core.dis_servisler.virus import KapaliTarayici, TaramaSonucu
from app.core.dosya_hatti import DosyaReddedildi, dosyayi_hazirla, gorunen_ad
from app.core.kanit_okuma.belge import ParcaTuru
from tests import dosya_ornekleri as ornek


def hazirla(ham, tarayici=None):
    return asyncio.run(dosyayi_hazirla(ham, tarayici or KapaliTarayici()))


def test_pdf_javascript_ve_gomulu_dosya_temizlenir():
    hazir = hazirla(ornek.pdf(javascript=True, ek_dosya=True))
    assert hazir.parca_turu is ParcaTuru.DOSYA
    assert hazir.tarama is TaramaSonucu.TARANMADI
    with pikepdf.open(io.BytesIO(hazir.veri)) as temiz:
        assert "/OpenAction" not in temiz.Root
        assert len(temiz.attachments) == 0


def test_gorsel_yeniden_kodlanir_exif_on_okunur_sonra_silinir():
    hazir = hazirla(ornek.gorsel("JPEG", exif=True))
    assert hazir.parca_turu is ParcaTuru.GORSEL
    assert hazir.on_bilgi["exif"] == {"uretici": "Telefonum", "yazilim": "Duzenleyici 1.0"}
    with Image.open(io.BytesIO(hazir.veri)) as temiz:
        assert len(temiz.getexif()) == 0


def test_cok_bicimli_dosya_etkisizlesir():
    """PNG'nin sonuna eklenmiş betik yeniden kodlamada düşer."""
    ham = ornek.gorsel("PNG") + b"<script>alert(1)</script>"
    assert b"<script>" not in hazirla(ham).veri


def test_ozet_ham_dosyadan():
    ham = ornek.gorsel("PNG")
    assert hazirla(ham).ozet == hazirla(ham).ozet


@pytest.mark.parametrize(
    "ham", [b"<html>merhaba</html>", b"MZ\x90\x00" + b"\x00" * 100, b"GIF89a" + b"\x00" * 20]
)
def test_desteklenmeyen_tur_reddedilir(ham):
    with pytest.raises(DosyaReddedildi, match="Yalnızca PDF"):
        hazirla(ham)


def test_uzanti_degil_icerik_belirler():
    """Adı .pdf olan HTML yine reddedilir: tür ilk baytlardan."""
    with pytest.raises(DosyaReddedildi):
        hazirla(b"<html><body>sahte.pdf</body></html>")


def test_boyut_siniri(monkeypatch):
    monkeypatch.setitem(
        dosya_hatti.TURLER,
        "image/png",
        dosya_hatti.DosyaTuru("image/png", ParcaTuru.GORSEL, 10),
    )
    with pytest.raises(DosyaReddedildi, match="çok büyük"):
        hazirla(ornek.gorsel("PNG"))


def test_zararli_dosya_reddedilir():
    class Zararli:
        kip = "sahte"

        async def tara(self, veri):
            return TaramaSonucu.ZARARLI

    with pytest.raises(DosyaReddedildi, match="zararlı"):
        hazirla(ornek.pdf(), Zararli())


def test_bozuk_pdf_reddedilir():
    with pytest.raises(DosyaReddedildi, match="açılamadı"):
        hazirla(b"%PDF-1.4\n bozuk")


def test_on_okuyucu_hatasi_yuklemeyi_dusurmez(monkeypatch):
    def bozuk(_ham, _tur):
        raise RuntimeError("okunamadı")

    monkeypatch.setitem(dosya_hatti.ON_OKUYUCULAR, "bozuk", bozuk)
    assert "bozuk" not in hazirla(ornek.gorsel("PNG")).on_bilgi


@pytest.mark.parametrize(
    ("ham_ad", "beklenen"),
    [
        (r"C:\Users\elif\rapor.pdf", "rapor.pdf"),
        ("../../etc/passwd", "passwd"),
        ("satır\nsonu.pdf", "satırsonu.pdf"),
        ("", "kanit.pdf"),
        (None, "kanit.pdf"),
    ],
)
def test_gorunen_ad(ham_ad, beklenen):
    assert gorunen_ad(ham_ad, "application/pdf") == beklenen
