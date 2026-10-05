"""Görselin internetteki kaynağını arama: arayüz, Cloud Vision ve kapalı kip (plan § 4.3, § 14.4).

Yüklenen görselin birebir eşi başka bir sayfada var mı? (`gorsel_baskasinda`.)
Varsayılan kapalı (`GORSEL_ARAYICI=kapali`); açıkken yalnızca tasarım / fotoğraf
alanındaki görsellerde ve aylık tavan dolmadıysa çağrılır (karar servisin).
Görsel yurt dışındaki bir servise gider; KVKK aydınlatma metninde listelidir.

Cloud Vision Web Detection tarih vermez: "daha eski tarihte" sorusu yanıtsız
kalır, GİRVAK sayfayı açıp bakar (plan § 18). Anahtar URL'de değil başlıkta
gider (log'a düşmesin). Görsel gönderilmeden önce küçültülür (istek sınırı
10 MB; kaynak araması için 1024 px yeter).

Zarif düşüş (İ9): servis hata verirse `None`; sinyal yalnızca eksik kalır.
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.dis_servisler.sarmalayicilar import gozlemli, zaman_asimli

logger = logging.getLogger("zemin360.gorsel_arayici")

ARAMA_KENARI = 1024
EN_COK_SAYFA = 20


@dataclass(frozen=True)
class EslesenSayfa:
    adres: str
    baslik: str | None
    # Sayfada görselin birebir eşi var (kısmi / benzer eşleşmeler sinyal değil)
    tam_eslesme: bool


@dataclass(frozen=True)
class AramaSonucu:
    sayfalar: tuple[EslesenSayfa, ...]


class GorselArayici(Protocol):
    # "cloud_vision" | "kapali"
    kip: str

    async def ara(self, veri: bytes) -> AramaSonucu | None: ...


def arama_gorseli(veri: bytes) -> bytes:
    """Uzun kenarı en çok `ARAMA_KENARI` piksel JPEG (servise giden kopya)."""
    from PIL import Image

    with Image.open(io.BytesIO(veri)) as gorsel:
        kopya = gorsel.convert("RGB")
        kopya.thumbnail((ARAMA_KENARI, ARAMA_KENARI))
        cikti = io.BytesIO()
        kopya.save(cikti, format="JPEG", quality=85)
    return cikti.getvalue()


def sonucu_coz(yanit: dict[str, Any]) -> AramaSonucu | None:
    """Web Detection yanıtı → sayfalar. Hata gövdesi ya da beklenmeyen biçim → None."""
    cevaplar = yanit.get("responses") if isinstance(yanit, dict) else None
    if not isinstance(cevaplar, list) or not cevaplar or not isinstance(cevaplar[0], dict):
        return None
    if cevaplar[0].get("error"):
        logger.warning("cloud vision hata dondu: %s", cevaplar[0]["error"])
        return None
    web = cevaplar[0].get("webDetection") or {}
    sayfalar = []
    for sayfa in (web.get("pagesWithMatchingImages") or [])[:EN_COK_SAYFA]:
        adres = sayfa.get("url") if isinstance(sayfa, dict) else None
        if not isinstance(adres, str) or not adres.startswith(("http://", "https://")):
            continue
        baslik = sayfa.get("pageTitle")
        sayfalar.append(
            EslesenSayfa(
                adres=adres,
                baslik=baslik.strip()[:200] if isinstance(baslik, str) and baslik.strip() else None,
                tam_eslesme=bool(sayfa.get("fullMatchingImages")),
            )
        )
    return AramaSonucu(tuple(sayfalar))


class CloudVisionArayici:
    kip = "cloud_vision"
    ADRES = "https://vision.googleapis.com/v1/images:annotate"

    def __init__(
        self,
        api_anahtari: str,
        zaman_asimi_sn: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_anahtari = api_anahtari
        self._zaman_asimi_sn = zaman_asimi_sn
        self._transport = transport
        self._iste = gozlemli("gorsel_arayici")(zaman_asimli(zaman_asimi_sn)(self._servise_sor))

    async def ara(self, veri: bytes) -> AramaSonucu | None:
        try:
            kopya = await asyncio.to_thread(arama_gorseli, veri)
            return sonucu_coz(await self._iste(kopya))
        except Exception:  # zarif düşüş: gözlemli hatayı sağlığa ve log'a yazdı
            return None

    async def _servise_sor(self, veri: bytes) -> dict:
        govde = {
            "requests": [
                {
                    "image": {"content": base64.b64encode(veri).decode()},
                    "features": [{"type": "WEB_DETECTION", "maxResults": EN_COK_SAYFA}],
                }
            ]
        }
        async with httpx.AsyncClient(
            timeout=self._zaman_asimi_sn, transport=self._transport
        ) as istemci:
            yanit = await istemci.post(
                self.ADRES, json=govde, headers={"X-Goog-Api-Key": self._api_anahtari}
            )
        yanit.raise_for_status()
        return yanit.json()


class KapaliGorselArayici:
    """Null Object: kaynak araması yok (varsayılan)."""

    kip = "kapali"

    async def ara(self, veri: bytes) -> AramaSonucu | None:
        return None
