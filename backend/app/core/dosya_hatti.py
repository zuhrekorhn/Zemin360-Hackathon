"""Yüklenen kanıt dosyasının güvenli hale getirilmesi (plan § 4.4; Pipeline deseni, § 14.3).

Sıra tek yerde, her adım tek iş yapar:
  1. Tür: ilk baytlardan (`filetype`); uzantıya ve istemcinin söylediğine bakılmaz.
  2. Boyut: PDF 20 MB, görsel 10 MB.
  3. Virüs: ClamAV; yalnızca "zararlı" reddeder (tarayıcı kapalıysa geçer).
  4. Ön okuma: temizlik dosyanın gömülü verisini siler (EXIF, C2PA, rozet
     verisi, e-imzanın bayt aralığı); bu yüzden onlar temizlikten ÖNCE ham
     dosyadan okunur. Ön okuyucular `ON_OKUYUCULAR`'a kayıtlıdır (açık / kapalı:
     yeni çapa = yeni satır).
  5. Temizlik: PDF'te JavaScript, otomatik eylemler ve gömülü dosyalar
     (`pikepdf`); görsel Pillow ile yeniden kodlanır, meta veri ve çok biçimli
     (polyglot) içerik düşer.
Depoya konan temizlenmiş dosyadır; tekrar denetimi için özet ham dosyadan, görselin
algısal özeti (pHash) temizlenmiş piksellerden alınır.
Veritabanı ve ağ yok (virüs tarayıcı dışarıdan verilir).
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import filetype

from app.core.dis_servisler.virus import TaramaSonucu, VirusTarayici
from app.core.gorsel_ozeti import algisal_ozet
from app.core.kanit_okuma.belge import ParcaTuru

logger = logging.getLogger("zemin360.dosya_hatti")

MB = 1024 * 1024


@dataclass(frozen=True)
class DosyaTuru:
    icerik_turu: str
    parca_turu: ParcaTuru
    azami_boyut: int


# Kabul edilen türler (ilk baytlardan). HEIC temizlikte JPEG'e çevrilir.
TURLER: dict[str, DosyaTuru] = {
    "application/pdf": DosyaTuru("application/pdf", ParcaTuru.DOSYA, 20 * MB),
    "image/png": DosyaTuru("image/png", ParcaTuru.GORSEL, 10 * MB),
    "image/jpeg": DosyaTuru("image/jpeg", ParcaTuru.GORSEL, 10 * MB),
    "image/webp": DosyaTuru("image/webp", ParcaTuru.GORSEL, 10 * MB),
    "image/heic": DosyaTuru("image/heic", ParcaTuru.GORSEL, 10 * MB),
}
AZAMI_BOYUT = max(t.azami_boyut for t in TURLER.values())
# Sıkıştırma bombası: bundan büyük görsel açılmaz.
AZAMI_PIKSEL = 60_000_000


class DosyaReddedildi(ValueError):
    """Dosya kabul edilmedi; mesaj gence gösterilir (uçta 422)."""


@dataclass(frozen=True)
class HazirDosya:
    veri: bytes
    # Temizlenmemiş dosya: çapa doğrulaması (imza bayt aralığı, rozet verisi) için
    ham: bytes = field(repr=False)
    icerik_turu: str
    parca_turu: ParcaTuru
    # Ham dosyanın SHA-256'sı (tekrar denetimi, plan § 4.4)
    ozet: str
    tarama: TaramaSonucu
    # Ön okuyucuların çıktısı: {"exif": {...}, "c2pa": {...}, ...}
    on_bilgi: dict[str, Any] = field(default_factory=dict)
    # Görselin algısal özeti (temizlenmiş, yönü düzeltilmiş piksellerden); PDF'te None
    phash: str | None = None


# Ön okuyucu: (ham veri, içerik türü) → JSON'a yazılabilir sözlük ya da None.
OnOkuyucu = Callable[[bytes, str], dict[str, Any] | None]
ON_OKUYUCULAR: dict[str, OnOkuyucu] = {}


def on_okuyucu(ad: str) -> Callable[[OnOkuyucu], OnOkuyucu]:
    def kaydet(fonk: OnOkuyucu) -> OnOkuyucu:
        ON_OKUYUCULAR[ad] = fonk
        return fonk

    return kaydet


def gorunen_ad(ham_ad: str | None, icerik_turu: str) -> str:
    """Yalnızca gösterim için: yol, denetim karakterleri ve aşırı uzunluk atılır.
    Depo anahtarı hiçbir zaman bundan türemez."""
    ad = (ham_ad or "").replace("\\", "/").rsplit("/", 1)[-1]
    ad = "".join(c for c in unicodedata.normalize("NFC", ad) if unicodedata.category(c)[0] != "C")
    ad = re.sub(r"\s+", " ", ad).strip()[:120]
    return ad or ("kanit.pdf" if icerik_turu == "application/pdf" else "gorsel")


def tur_belirle(ham: bytes) -> DosyaTuru:
    tahmin = filetype.guess(ham[:8192])
    mime = tahmin.mime if tahmin else None
    if mime == "image/heif":
        mime = "image/heic"
    if mime not in TURLER:
        raise DosyaReddedildi("Yalnızca PDF, PNG, JPEG, WebP ya da HEIC yükleyebilirsin.")
    return TURLER[mime]


def boyut_denetle(ham: bytes, tur: DosyaTuru) -> None:
    if len(ham) > tur.azami_boyut:
        sinir = tur.azami_boyut // MB
        raise DosyaReddedildi(f"Bu dosya çok büyük; en çok {sinir} MB yükleyebilirsin.")
    if not ham:
        raise DosyaReddedildi("Dosya boş görünüyor.")


def on_oku(ham: bytes, icerik_turu: str) -> dict[str, Any]:
    """Kayıtlı ön okuyucular; biri hata verirse o bilgi yalnızca eksik kalır (İ9)."""
    sonuc: dict[str, Any] = {}
    for ad, okuyucu in ON_OKUYUCULAR.items():
        try:
            bilgi = okuyucu(ham, icerik_turu)
        except Exception:
            logger.warning("on_okuyucu=%s hata verdi", ad, exc_info=True)
            continue
        if bilgi:
            sonuc[ad] = bilgi
    return sonuc


# --- Temizlik ----------------------------------------------------------------------------

_TEHLIKELI_EYLEMLER = {"/JavaScript", "/Launch", "/SubmitForm", "/ImportData", "/GoToR"}


def pdf_temizle(ham: bytes) -> bytes:
    import pikepdf

    try:
        pdf = pikepdf.open(io.BytesIO(ham))
    except pikepdf.PasswordError as hata:
        raise DosyaReddedildi("Şifreli PDF'i okuyamıyoruz; şifresiz bir kopyasını yükle.") from hata
    except pikepdf.PdfError as hata:
        raise DosyaReddedildi("Bu PDF açılamadı; dosya bozuk olabilir.") from hata
    with pdf:
        kok = pdf.Root
        for anahtar in ("/OpenAction", "/AA", "/AcroForm"):
            if anahtar in kok:
                del kok[anahtar]
        if "/Names" in kok:
            for anahtar in ("/JavaScript", "/EmbeddedFiles"):
                if anahtar in kok.Names:
                    del kok.Names[anahtar]
        for sayfa in pdf.pages:
            if "/AA" in sayfa.obj:
                del sayfa.obj["/AA"]
            for ek in list(sayfa.obj.get("/Annots", [])):
                if ek.get("/Subtype") == "/FileAttachment":
                    ek.Subtype = pikepdf.Name("/Text")
                    for alan in ("/FS", "/A"):
                        if alan in ek:
                            del ek[alan]
                eylem = ek.get("/A")
                if eylem is not None and str(eylem.get("/S")) in _TEHLIKELI_EYLEMLER:
                    del ek["/A"]
                if "/AA" in ek:
                    del ek["/AA"]
        cikti = io.BytesIO()
        pdf.save(cikti)
        return cikti.getvalue()


def gorsel_temizle(ham: bytes, icerik_turu: str) -> tuple[bytes, str]:
    """Yeniden kodlama: yalnızca pikseller kalır. Döner: (veri, yeni içerik türü)."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    _heif_kaydet()
    Image.MAX_IMAGE_PIXELS = AZAMI_PIKSEL
    try:
        with Image.open(io.BytesIO(ham)) as gorsel:
            gorsel.load()
            # Yön EXIF'te; silinmeden önce piksellere uygulanır.
            duz = ImageOps.exif_transpose(gorsel)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as hata:
        raise DosyaReddedildi(
            "Bu görsel açılamadı; dosya bozuk ya da çok büyük olabilir."
        ) from hata

    hedef = {"image/png": "PNG", "image/webp": "WEBP"}.get(icerik_turu, "JPEG")
    if hedef == "JPEG" and duz.mode not in ("RGB", "L"):
        duz = duz.convert("RGB")
    cikti = io.BytesIO()
    duz.save(cikti, format=hedef, **({"quality": 90} if hedef != "PNG" else {}))
    return cikti.getvalue(), f"image/{hedef.lower()}"


def _heif_kaydet() -> None:
    from pillow_heif import register_heif_opener

    register_heif_opener()


@on_okuyucu("exif")
def exif_oku(ham: bytes, icerik_turu: str) -> dict[str, Any] | None:
    """Zayıf sinyal (plan § 4.3): cihaz, yazılım, çekim tarihi. Konum OKUNMAZ."""
    if not icerik_turu.startswith("image/"):
        return None
    from PIL import ExifTags, Image

    _heif_kaydet()
    with Image.open(io.BytesIO(ham)) as gorsel:
        exif = gorsel.getexif()
    alanlar = {
        ExifTags.Base.Make: "uretici",
        ExifTags.Base.Model: "model",
        ExifTags.Base.Software: "yazilim",
        ExifTags.Base.DateTime: "tarih",
    }
    bilgi = {ad: str(exif[etiket])[:80] for etiket, ad in alanlar.items() if etiket in exif}
    return bilgi or None


async def dosyayi_hazirla(ham: bytes, tarayici: VirusTarayici) -> HazirDosya:
    tur = tur_belirle(ham)
    boyut_denetle(ham, tur)
    tarama = await tarayici.tara(ham)
    if tarama is TaramaSonucu.ZARARLI:
        raise DosyaReddedildi("Bu dosyada zararlı içerik bulundu; yüklenmedi.")
    on_bilgi = await asyncio.to_thread(on_oku, ham, tur.icerik_turu)
    if tur.parca_turu is ParcaTuru.DOSYA:
        veri, icerik_turu = await asyncio.to_thread(pdf_temizle, ham), tur.icerik_turu
        phash = None
    else:
        veri, icerik_turu = await asyncio.to_thread(gorsel_temizle, ham, tur.icerik_turu)
        phash = await asyncio.to_thread(algisal_ozet, veri)
    return HazirDosya(
        veri=veri,
        ham=ham,
        icerik_turu=icerik_turu,
        parca_turu=tur.parca_turu,
        ozet=hashlib.sha256(ham).hexdigest(),
        tarama=tarama,
        on_bilgi=on_bilgi,
        phash=phash,
    )
