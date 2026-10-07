"""Dosyadaki QR ve barkodların okunması, doğrulama adreslerinin ayıklanması (docs/dogrulama.md
§ 4.2).

PDF'in ilk sayfaları görüntüye çevrilir (`pypdfium2`), kodlar `zxing-cpp` ile
okunur. Ön okuyucu olarak kayıtlıdır (`core/dosya_hatti.py`): yeniden
kodlamadan önce ham dosyadan çalışır. Doğrulama adresi önce kodlardan, sonra
metindeki doğrulama ipucu taşıyan ya da bilinen düzenleyene giden adreslerden
alınır.
"""

from __future__ import annotations

import io
import re
import threading
from typing import Any

from app.core.capalar.duzenleyenler import duzenleyen
from app.core.dosya_hatti import on_okuyucu
from app.core.kanit_okuma.adres import normal_url

TARANACAK_SAYFA = 3
AZAMI_ADRES = 3
_ADRES = re.compile(r"https?://[^\s<>\"'()\[\]]+", re.IGNORECASE)
# PDFium iş parçacığı güvenli değil: aynı süreçte iki çağrı aynı anda çalışırsa süreç
# çöker (dosya hattı ön okuyucuları iş parçacığı havuzunda paralel çalıştırır). Bütün
# pypdfium2 çağrıları bu kilidin içinde; QR okuma (zxing) kilit dışında kalır.
_PDFIUM_KILIDI = threading.Lock()

_IPUCU = re.compile(
    r"verif|dogrula|doğrula|validate|credential|certificate|sertifika|badge|rozet|belge",
    re.IGNORECASE,
)


def _goruntuler(ham: bytes, icerik_turu: str) -> list[Any]:
    from PIL import Image

    if icerik_turu == "application/pdf":
        import pypdfium2 as pdfium

        with _PDFIUM_KILIDI:
            belge = pdfium.PdfDocument(ham)
            try:
                return [
                    belge[i].render(scale=2).to_pil()
                    for i in range(min(len(belge), TARANACAK_SAYFA))
                ]
            finally:
                belge.close()
    with Image.open(io.BytesIO(ham)) as gorsel:
        gorsel.load()
        return [gorsel.convert("RGB")]


@on_okuyucu("kodlar")
def kodlari_oku(ham: bytes, icerik_turu: str) -> dict[str, Any] | None:
    import zxingcpp

    kodlar: list[dict[str, str]] = []
    for goruntu in _goruntuler(ham, icerik_turu):
        for kod in zxingcpp.read_barcodes(goruntu):
            if kod.text and all(k["metin"] != kod.text for k in kodlar):
                kodlar.append({"bicim": str(kod.format.name), "metin": kod.text[:500]})
    return {"liste": kodlar} if kodlar else None


def dogrulama_adresleri(kodlar: list[dict[str, str]], metin: str) -> list[str]:
    """Kodlardaki adresler önce; metinde yalnızca ipucu taşıyan ya da bilinen
    düzenleyene giden adresler. Normal biçimde tekil, en çok `AZAMI_ADRES`."""
    adaylar = [k["metin"].strip() for k in kodlar if _ADRES.fullmatch(k["metin"].strip())]
    for adres in _ADRES.findall(metin or ""):
        adres = adres.rstrip(".,;:")
        if _IPUCU.search(adres) or duzenleyen(adres):
            adaylar.append(adres)
    tekil: dict[str, str] = {}
    for adres in adaylar:
        tekil.setdefault(normal_url(adres), adres)
    return list(tekil.values())[:AZAMI_ADRES]
