"""LLM sağlayıcısı ve yedek model zinciri.

Hem sohbet ajanları (yapılandırılmış çıkarım) hem Eşleştirme Ajanı (düz metin
gerekçe) buradan geçiyor. Ortak olan tek şey sağlayıcı ve kota davranışı:
Gemini ücretsiz katmanında günlük kota MODEL BAŞINA ayrı işliyor, bu yüzden
ana modelin kotası dolunca aynı çağrı yedek modele düşer. Aynı şey sağlayıcı
kaynaklı geçici arızalarda (5xx, örn. "503 UNAVAILABLE — high demand") da
geçerli: yoğunluk model başına oluştuğu için yedek model çoğu zaman boştadır.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import GoogleAPIError, GoogleRateLimitError

from app.core.config import get_settings

logger = logging.getLogger("zemin360.llm")

# Sağlayıcı SDK'sının kendi tekrarları. Varsayılan 6 ve üstel bekleme ile
# 503'te dakikalara çıkabiliyor — yedek modele geçmeden önce boşuna beklemek
# oluyor. Asıl tekrar stratejimiz yedek MODEL (aynı modeli tekrar denemek
# yoğunluk anında zaten işe yaramıyor), o yüzden burada tek bir hızlı tekrar
# bırakıyoruz. Kütüphane 1'i "hiç tekrar yok" sayıyor, 2 = bir tekrar.
MAKS_TEKRAR = 2


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


class SureOlcer(BaseCallbackHandler):
    """Her LLM çağrısının süresini ve kaçıncı deneme olduğunu log'a yazar.

    Yavaşlığın nerede olduğunu görmek için: tek bir istek içinde ana model
    denenip yedeğe düşüldüyse iki satır çıkar, ikisinin de süresi ayrı ayrı
    görünür. Sağlayıcı SDK'sının kendi içindeki HTTP tekrarları buraya
    yansımıyor — onları `MAKS_TEKRAR` sınırlıyor.
    """

    def __init__(self) -> None:
        self._baslangiclar: dict[uuid.UUID, float] = {}
        self._deneme: dict[uuid.UUID, int] = {}

    def _kok(self, parent_run_id: uuid.UUID | None, run_id: uuid.UUID) -> uuid.UUID:
        return parent_run_id or run_id

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self._baslangiclar[run_id] = time.perf_counter()
        kok = self._kok(parent_run_id, run_id)
        self._deneme[kok] = self._deneme.get(kok, 0) + 1

    def _bitir(self, run_id: uuid.UUID, parent_run_id: uuid.UUID | None) -> tuple[float, int]:
        baslangic = self._baslangiclar.pop(run_id, None)
        sure = time.perf_counter() - baslangic if baslangic else 0.0
        kok = self._kok(parent_run_id, run_id)
        return sure, self._deneme.get(kok, 1)

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        sure, deneme = self._bitir(run_id, parent_run_id)
        logger.info("LLM yanıtladı: %.2f sn, deneme %d", sure, deneme)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        sure, deneme = self._bitir(run_id, parent_run_id)
        logger.warning("LLM hatası: %.2f sn, deneme %d — %s", sure, deneme, error)


def model(model_adi: str) -> ChatGoogleGenerativeAI:
    ayarlar = get_settings()
    if not ayarlar.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY tanımlı değil (.env)")
    return ChatGoogleGenerativeAI(
        model=model_adi,
        google_api_key=ayarlar.google_api_key,
        temperature=0,
        max_retries=MAKS_TEKRAR,
        callbacks=[SureOlcer()],
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
