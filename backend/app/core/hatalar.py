"""Uygulama geneli hata işleyicileri.

Neden gerekli: yakalanmayan bir istisna Starlette'te en dıştaki katmanda
(`ServerErrorMiddleware`) yanıta dönüşüyor — yani CORSMiddleware'in DIŞINDA.
Sonuç, düz metin bir 500 ve CORS başlığı olmayan bir yanıt; tarayıcı bunu
ağ hatası sayıyor ve kullanıcı "Backend'e ulaşılamadı" görüyor. Backend
ayaktayken bu cümle yanlış ve hata ayıklamayı zorlaştırıyor.

Bu yüzden işleyiciler CORS başlıklarını kendileri ekliyor. Gövde her zaman
FastAPI'nin alıştığımız biçiminde: {"detail": "..."} — istemci tarafındaki
tek bir okuma yolu yeterli olsun.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.llm import HizSinirHatasi, ModelMesgulHatasi

logger = logging.getLogger("zemin360")

# Kullanıcıya gösterilen metin: ne olduğunu söyler, iç ayrıntı sızdırmaz.
# Yığın izi ve hata mesajı log'a yazılır (sunucu günlüğü).
# Hitapsız: genç ("sen") ve firma ("siz") aynı cümleyi görür (docs/icerik-rehberi.md § 3).
BEKLENMEYEN_MESAJ = "Beklenmeyen bir sorun oldu, isteği tamamlayamadık."
# 429: iki model de hız sınırına takıldı (ücretli katmanda dakikalık sınır;
# ücretsiz katmandaki günlük kota değil). Birkaç saniye içinde geçer.
HIZ_SINIRI_MESAJI = "Şu an çok yoğunuz, isteğe yanıt veremedik. Biraz sonra yeniden denenebilir."
MESGUL_MESAJI = "Şu an yanıt veremedik. Birkaç saniye sonra yeniden denenebilir."


def _cors_basliklari(istek: Request) -> dict[str, str]:
    """İsteğin origin'i izinliyse CORS başlıklarını üretir.

    CORSMiddleware'in yaptığının küçük bir kopyası; burada gerekli çünkü bu
    yanıtlar o katmandan geçmiyor.
    """
    origin = istek.headers.get("origin")
    if not origin:
        return {}
    izinliler = get_settings().cors_origin_list
    if origin not in izinliler and "*" not in izinliler:
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Vary": "Origin",
    }


def _yanit(istek: Request, durum_kodu: int, mesaj: str) -> JSONResponse:
    return JSONResponse(
        status_code=durum_kodu, content={"detail": mesaj}, headers=_cors_basliklari(istek)
    )


async def beklenmeyen_hata(istek: Request, hata: Exception) -> JSONResponse:
    logger.exception("Beklenmeyen hata: %s %s", istek.method, istek.url.path)
    return _yanit(istek, 500, BEKLENMEYEN_MESAJ)


async def hiz_siniri_hatasi(istek: Request, hata: Exception) -> JSONResponse:
    logger.warning("LLM hız sınırı: %s %s — %s", istek.method, istek.url.path, hata)
    return _yanit(istek, 429, HIZ_SINIRI_MESAJI)


async def mesgul_hatasi(istek: Request, hata: Exception) -> JSONResponse:
    """Sağlayıcı geçici olarak yanıt veremedi (5xx).

    Yedek model zinciri zaten denenmiş demektir (bkz. app/core/llm.py);
    buraya düştüyse iki model de meşgul. 503 dönüyoruz: istemci için
    "sende bir sorun yok, sonra dene" anlamı taşıyan doğru kod.
    """
    logger.warning("LLM meşgul: %s %s — %s", istek.method, istek.url.path, hata)
    return _yanit(istek, 503, MESGUL_MESAJI)


def hata_isleyicilerini_kur(app: FastAPI) -> None:
    app.add_exception_handler(HizSinirHatasi, hiz_siniri_hatasi)
    app.add_exception_handler(ModelMesgulHatasi, mesgul_hatasi)
    app.add_exception_handler(Exception, beklenmeyen_hata)
