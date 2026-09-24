"""LLM sağlayıcısı ve yedek model zinciri.

Hem sohbet ajanları (yapılandırılmış çıkarım) hem Eşleştirme Ajanı (düz metin
gerekçe) buradan geçiyor. Ortak olan tek şey sağlayıcı ve kota davranışı:
Gemini ücretsiz katmanında günlük kota MODEL BAŞINA ayrı işliyor, bu yüzden
ana modelin kotası dolunca aynı çağrı yedek modele düşer. Aynı şey sağlayıcı
kaynaklı geçici arızalarda (5xx, örn. "503 UNAVAILABLE — high demand") da
geçerli: yoğunluk model başına oluştuğu için yedek model çoğu zaman boştadır.
"""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import GoogleAPIError, GoogleRateLimitError

from app.core.config import get_settings


class HizSinirHatasi(RuntimeError):
    """LLM sağlayıcısı kotayı doldurdu (Gemini ücretsiz katman)."""


class ModelMesgulHatasi(RuntimeError):
    """Sağlayıcı geçici olarak yanıt veremedi (5xx). Kullanıcı hatası değil.

    Kotadan ayrı tutuluyor: kota günlük ve beklemek gerekir, bu ise saniyeler
    sürebilen anlık bir yoğunluk. İkisi kullanıcıya farklı şey söylüyor.
    """


def kota_hatasi_mi(hata: Exception) -> bool:
    metin = str(hata)
    return "RESOURCE_EXHAUSTED" in metin or "429" in metin


def mesgul_hatasi_mi(hata: Exception) -> bool:
    """Sağlayıcı kaynaklı geçici arıza mı? (503/UNAVAILABLE, 500, 502, 504)"""
    if isinstance(hata, GoogleAPIError):
        return True
    metin = str(hata)
    return "UNAVAILABLE" in metin or any(kod in metin for kod in ("500", "502", "503", "504"))


def llm_hatasini_cevir(hata: Exception) -> Exception:
    """Sağlayıcı hatasını ajanların ortak diline çevirir.

    Kota ve geçici arıza dışındaki hatalar (hatalı istek, kimlik doğrulama)
    olduğu gibi geçer — onları yutmak sorunu gizlerdi.
    """
    if kota_hatasi_mi(hata):
        return HizSinirHatasi(str(hata))
    if mesgul_hatasi_mi(hata):
        return ModelMesgulHatasi(str(hata))
    return hata


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

    Yedeğe düşüren iki durum var: kota (`GoogleRateLimitError`) ve sağlayıcı
    kaynaklı geçici arıza (`GoogleAPIError` — kütüphane bunu yalnızca 5xx
    için üretiyor). 4xx hataları listede YOK: hatalı bir istek ikinci modelde
    de aynı şekilde başarısız olur, boşuna çağrı yapmanın anlamı yok.
    """
    ayarlar = get_settings()
    return zincir_kur(ayarlar.gemini_model).with_fallbacks(
        [zincir_kur(ayarlar.gemini_yedek_model)],
        exceptions_to_handle=(GoogleRateLimitError, GoogleAPIError),
    )
