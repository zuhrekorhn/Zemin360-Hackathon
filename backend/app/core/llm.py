"""LLM sağlayıcısı ve yedek model zinciri.

Hem sohbet ajanları (yapılandırılmış çıkarım) hem Eşleştirme Ajanı (düz metin
gerekçe) buradan geçiyor. Ortak olan tek şey sağlayıcı ve kota davranışı:
Gemini ücretsiz katmanında günlük kota MODEL BAŞINA ayrı işliyor, bu yüzden
ana modelin kotası dolunca aynı çağrı yedek modele düşer.
"""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import GoogleRateLimitError

from app.core.config import get_settings


class HizSinirHatasi(RuntimeError):
    """LLM sağlayıcısı kotayı doldurdu (Gemini ücretsiz katman)."""


def kota_hatasi_mi(hata: Exception) -> bool:
    metin = str(hata)
    return "RESOURCE_EXHAUSTED" in metin or "429" in metin


def model(model_adi: str) -> ChatGoogleGenerativeAI:
    ayarlar = get_settings()
    if not ayarlar.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY tanımlı değil (.env)")
    return ChatGoogleGenerativeAI(
        model=model_adi,
        google_api_key=ayarlar.google_api_key,
        temperature=0,
    )


def yedekli_zincir(zincir_kur: Callable[[str], Runnable]) -> Runnable:
    """Aynı zinciri ana ve yedek modelle kurup birbirine bağlar.

    `zincir_kur` bir model adı alır ve o modelle çalışan zinciri döner —
    böylece yapılandırılmış çıktı da, düz metin de aynı yedekleme desenini
    kullanabiliyor. Yedeğin de kotası dolarsa hata çağırana kadar çıkar.
    """
    ayarlar = get_settings()
    return zincir_kur(ayarlar.gemini_model).with_fallbacks(
        [zincir_kur(ayarlar.gemini_yedek_model)],
        exceptions_to_handle=(GoogleRateLimitError,),
    )
