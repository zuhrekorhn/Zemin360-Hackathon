"""Open Badges rozet verisinin okunması (docs/dogrulama.md § 4.2).

Rozet PNG'sinin içine gömülü veri (`openbadges` iTXt / tEXt bloğu; OB 1.0 / 2.0)
ham dosyadan okunur: yeniden kodlama onu siler. Veri ya iddianın kendisidir
(JSON), ya iddianın adresi, ya da imzalı iddiadır (JWS).

Alıcı karşılaştırması: OB 2.0'da alıcı çoğunlukla `sha256$<özet>` biçiminde,
tuzlu e-posta özetidir; hesap e-postasıyla aynı yoldan hesaplanıp karşılaştırılır.
Saf yardımcılar; ağ isteği doğrulayıcıda (`servisler/dogrulama/capalar/rozet.py`).
"""

from __future__ import annotations

import hashlib
import io
import json
import re
from typing import Any

from app.core.dosya_hatti import on_okuyucu

AZAMI_VERI = 8000
_JWS = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*$")


@on_okuyucu("rozet")
def rozet_verisini_oku(ham: bytes, icerik_turu: str) -> dict[str, Any] | None:
    if icerik_turu != "image/png":
        return None
    from PIL import Image

    with Image.open(io.BytesIO(ham)) as gorsel:
        veri = (getattr(gorsel, "text", None) or {}).get("openbadges")
    if not veri:
        return None
    return {"veri": str(veri).strip()[:AZAMI_VERI]}


def rozet_bicimi(veri: str) -> str:
    """Verinin biçimi: iddia (JSON), adres (http) ya da imzali (JWS)."""
    if veri.startswith("{"):
        return "iddia"
    if veri.startswith(("http://", "https://")):
        return "adres"
    if _JWS.match(veri):
        return "imzali"
    return "bilinmiyor"


def iddia_json(veri: str) -> dict[str, Any] | None:
    try:
        deger = json.loads(veri)
    except ValueError:
        return None
    return deger if isinstance(deger, dict) else None


def iddia_adresi(iddia: dict[str, Any]) -> str | None:
    """Barındırılan (hosted) doğrulamanın adresi: OB 2.0 `id`, OB 1.0 `verify.url`."""
    dogrulama = iddia.get("verification") or iddia.get("verify") or {}
    tur = str(dogrulama.get("type", "")).lower() if isinstance(dogrulama, dict) else ""
    if tur and "hosted" not in tur:
        return None
    adres = iddia.get("id") if isinstance(iddia.get("id"), str) else None
    if isinstance(dogrulama, dict) and isinstance(dogrulama.get("url"), str):
        adres = adres or dogrulama["url"]
    return adres if adres and adres.startswith("https://") else None


def alici_eslesir(alici: Any, eposta: str | None) -> tuple[bool, bool]:
    """(alıcı e-postayla mı tanımlı, hesap e-postasıyla eşleşiyor mu)."""
    if isinstance(alici, str):  # OB 1.0: "sha256$..." ya da düz e-posta
        alici = {"type": "email", "identity": alici, "hashed": alici.startswith("sha256$")}
    if not isinstance(alici, dict) or str(alici.get("type", "email")).lower() != "email":
        return False, False
    kimlik = str(alici.get("identity", ""))
    if not eposta or not kimlik:
        return True, False
    if alici.get("hashed") or kimlik.startswith(("sha256$", "md5$")):
        algoritma, _, ozet = kimlik.partition("$")
        if algoritma not in ("sha256", "md5"):
            return True, False
        tuz = str(alici.get("salt") or "")
        hesap = hashlib.new(algoritma, (eposta.strip().lower() + tuz).encode()).hexdigest()
        return True, hesap == ozet.lower()
    return True, kimlik.strip().lower() == eposta.strip().lower()
