"""LLM sağlayıcısı (Gemini, ücretli katman), model katmanları ve yedek zincir.

İki katman var (docs/architecture.md § LLM Maliyet/Performans Stratejisi):

    hizli — yapılandırılmış çıkarım: Keşif ve Tanımlama sohbetleri. Format
            net, ince akıl yürütme gerekmiyor; hız ve maliyet öncelikli.
    guclu — gerekçeli akıl yürütme: eşleştirme gerekçesi, doğrulama rubriği.
            Nüansın önemli olduğu, tek seferlik işler.

Model adları .env'den okunur (app/core/config.py), kod değişmeden değişir.

Her katmanın bir yedek modeli var. Amaç sağlayıcı kaynaklı arızada işi
tamamlamak: 5xx, zaman aşımı, anlık hız sınırı (429) ve kullanılamayan model
(404). Hepsi model başına oluşuyor, başka bir model o an çoğunlukla çalışır.
(Ücretsiz katmanda yedeğin asıl amacı günlük kotaydı; ücretli katmanda 429
dakikalık hız sınırı demek.)

Her çağrının süresi ve token kullanımı sunucu günlüğüne yazılır (`SureOlcer`).
Açılışta .env'deki model adları sağlayıcının listesiyle karşılaştırılır
(`model_adlarini_dogrula`); bulunamayan varsa uyarılır, uygulama durmaz.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import (
    GoogleAPIError,
    GoogleModelNotFoundError,
    GoogleRateLimitError,
)

from app.core.config import get_settings

logger = logging.getLogger("zemin360.llm")

Katman = Literal["hizli", "guclu"]

# Sağlayıcı SDK'sının kendi tekrarları. Varsayılan 6 ve üstel bekleme ile
# dakikalara çıkabiliyor. Asıl tekrar stratejimiz yedek MODEL: arıza ve hız
# sınırı model başına oluştuğu için aynı modeli tekrar tekrar denemek
# genellikle işe yaramıyor. Kütüphane 1'i "hiç tekrar yok" sayıyor, 2 = bir tekrar.
MAKS_TEKRAR = 2

# Yedek modele düşüren hatalar. 4xx'in geri kalanı (400 hatalı istek, 401/403
# yetki) listede YOK: aynı istek ikinci modelde de aynı şekilde başarısız olur.
YEDEGE_DUSUREN_HATALAR: tuple[type[BaseException], ...] = (
    GoogleAPIError,  # 5xx — kütüphane bu sınıfı yalnızca sunucu hataları için üretiyor
    GoogleRateLimitError,  # 429 — ücretli katmanda dakikalık hız sınırı
    httpx.TimeoutException,  # GEMINI_ZAMAN_ASIMI_SN aşıldı
    # 404 — model bulunamadı ya da yeni kullanıcılara kapatıldı. Model adresine
    # özgü bir sorun, başka model aynı istekte çalışır. Gerçek vaka:
    # gemini-2.5-pro models.list'te görünüyor ama çağrıda 404 dönüyor ve tüm
    # arka plan eşleştirmesini düşürmüştü. Log'a hata olarak yazılır ki
    # .env düzeltilsin (SureOlcer).
    GoogleModelNotFoundError,
)

# Katman → (ana model ayarı, yedek model ayarı). Log'da ve açılış kontrolünde
# "hangi .env değişkeni hangi modeli gösteriyor" diyebilmek için.
AYAR_ADLARI: dict[Katman, tuple[str, str]] = {
    "hizli": ("GEMINI_HIZLI_MODEL", "GEMINI_HIZLI_YEDEK_MODEL"),
    "guclu": ("GEMINI_GUCLU_MODEL", "GEMINI_GUCLU_YEDEK_MODEL"),
}


class HizSinirHatasi(RuntimeError):
    """Sağlayıcı hız sınırına takıldı (429) — iki model de. Kullanıcı hatası değil."""


class ModelMesgulHatasi(RuntimeError):
    """Sağlayıcı geçici olarak yanıt veremedi (5xx ya da zaman aşımı).

    Hız sınırından ayrı tutuluyor: kullanıcıya farklı cümle söylüyorlar
    (app/core/hatalar.py).
    """


def hiz_siniri_hatasi_mi(hata: Exception) -> bool:
    if isinstance(hata, GoogleRateLimitError):
        return True
    metin = str(hata)
    return "RESOURCE_EXHAUSTED" in metin or "429" in metin


def mesgul_hatasi_mi(hata: Exception) -> bool:
    """Sağlayıcı kaynaklı geçici arıza mı? (5xx, UNAVAILABLE, zaman aşımı)"""
    if isinstance(hata, GoogleAPIError | httpx.TimeoutException):
        return True
    metin = str(hata)
    return "UNAVAILABLE" in metin or any(kod in metin for kod in ("500", "502", "503", "504"))


def llm_hatasini_cevir(hata: Exception) -> Exception:
    """Sağlayıcı hatasını ajanların ortak diline çevirir.

    Hız sınırı ve geçici arıza dışındaki hatalar (hatalı istek, kimlik
    doğrulama) olduğu gibi geçer — onları yutmak sorunu gizlerdi.
    """
    if hiz_siniri_hatasi_mi(hata):
        return HizSinirHatasi(str(hata))
    if mesgul_hatasi_mi(hata):
        return ModelMesgulHatasi(str(hata) or type(hata).__name__)
    return hata


@dataclass
class KullanimToplayici:
    """Bir işin (ör. bir değerlendirmenin) bütün model çağrılarının toplam kullanımı."""

    cagri: int = 0
    girdi_token: int = 0
    cikti_token: int = 0


_TOPLAYICI: ContextVar[KullanimToplayici | None] = ContextVar("llm_kullanim", default=None)


@contextmanager
def kullanim_topla() -> Iterator[KullanimToplayici]:
    """İçerideki her model çağrısının token kullanımı toplayıcıya yazılır (gözlem, docs/dogrulama.md
    § 10.3).

    Çağrılar aynı görev içinde ya da `gather` ile açılan alt görevlerde olabilir:
    bağlam kopyalanır ama toplayıcı nesnesi paylaşılır.
    """
    toplayici = KullanimToplayici()
    belirtec = _TOPLAYICI.set(toplayici)
    try:
        yield toplayici
    finally:
        _TOPLAYICI.reset(belirtec)


def _kullanim_oku(response: Any) -> dict[str, Any] | None:
    try:
        return response.generations[0][0].message.usage_metadata or None
    except (AttributeError, IndexError, TypeError):
        return None


def _kullanimi_topla(response: Any) -> None:
    toplayici = _TOPLAYICI.get()
    if toplayici is None:
        return
    toplayici.cagri += 1
    kullanim = _kullanim_oku(response)
    if kullanim:
        toplayici.girdi_token += int(kullanim.get("input_tokens") or 0)
        toplayici.cikti_token += int(kullanim.get("output_tokens") or 0)


def _token_ozeti(response: Any) -> str:
    """LLM sonucundan token kullanımını okunur bir parçaya çevirir.

    Gemini'nin "düşünme" tokenları çıktı tokenlarının içinde sayılıyor ve
    çıktı olarak faturalanıyor; ayrıca gösteriliyor ki güçlü modellerin
    maliyeti neden yüksek, görülebilsin.
    """
    try:
        mesaj = response.generations[0][0].message
        kullanim = mesaj.usage_metadata
    except (AttributeError, IndexError, TypeError):
        kullanim = None
    if not kullanim:
        return "token bilgisi yok"

    dusunme = (kullanim.get("output_token_details") or {}).get("reasoning") or 0
    cikti = f"çıktı {kullanim.get('output_tokens', 0)}"
    if dusunme:
        cikti += f" (düşünme {dusunme})"
    return (
        f"girdi {kullanim.get('input_tokens', 0)}, {cikti}, "
        f"toplam {kullanim.get('total_tokens', 0)} token"
    )


class SureOlcer(BaseCallbackHandler):
    """Her LLM çağrısının işini, modelini, süresini ve token kullanımını log'a yazar.

    Tek bir istek içinde ana model denenip yedeğe düşüldüyse iki satır çıkar;
    model adından hangisinin yanıtladığı görünür. Sağlayıcı SDK'sının kendi
    içindeki HTTP tekrarları buraya yansımıyor — onları `MAKS_TEKRAR` sınırlıyor.
    """

    def __init__(self, is_adi: str, model_adi: str, ayar_adi: str | None = None) -> None:
        self.is_adi = is_adi
        self.model_adi = model_adi
        # Modeli seçen .env değişkeni (örn. GEMINI_GUCLU_MODEL); 404 uyarısında
        # neyin düzeltileceğini söylemek için.
        self.ayar_adi = ayar_adi
        self._baslangiclar: dict[uuid.UUID, float] = {}
        self._deneme: dict[uuid.UUID, int] = {}

    def _kok(self, parent_run_id: uuid.UUID | None, run_id: uuid.UUID) -> uuid.UUID:
        return parent_run_id or run_id

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[Any],
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self._baslat(run_id, parent_run_id)

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self._baslat(run_id, parent_run_id)

    def _baslat(self, run_id: uuid.UUID, parent_run_id: uuid.UUID | None) -> None:
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
        _kullanimi_topla(response)
        logger.info(
            "LLM yanıtladı [%s] %s: %.2f sn, deneme %d — %s",
            self.is_adi,
            self.model_adi,
            sure,
            deneme,
            _token_ozeti(response),
        )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        sure, deneme = self._bitir(run_id, parent_run_id)
        if isinstance(error, GoogleModelNotFoundError):
            logger.error(
                "MODEL KULLANILAMIYOR [%s] %s=%s — sağlayıcı bu modeli bulamadı ya da "
                "yeni kullanıcılara kapattı; bu çağrı yedek modele düşüyor. .env'de %s "
                "değişkenini çalışan bir modelle değiştir. Ayrıntı: %s",
                self.is_adi,
                self.ayar_adi or "model",
                self.model_adi,
                self.ayar_adi or "ilgili GEMINI_*",
                error,
            )
            return
        logger.warning(
            "LLM hatası [%s] %s: %.2f sn, deneme %d — %s: %s",
            self.is_adi,
            self.model_adi,
            sure,
            deneme,
            type(error).__name__,
            error,
        )


def katman_modelleri(katman: Katman) -> tuple[str, str]:
    """Katmanın (ana, yedek) model adları — .env'den."""
    ayarlar = get_settings()
    if katman == "hizli":
        return ayarlar.gemini_hizli_model, ayarlar.gemini_hizli_yedek_model
    return ayarlar.gemini_guclu_model, ayarlar.gemini_guclu_yedek_model


def model(
    model_adi: str,
    is_adi: str,
    ayar_adi: str | None = None,
    dusunme: str | None = None,
) -> ChatGoogleGenerativeAI:
    """`dusunme` verilirse Gemini 3'ün `thinking_level`'ı olarak iletilir."""
    ayarlar = get_settings()
    if not ayarlar.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY tanımlı değil (.env)")
    return ChatGoogleGenerativeAI(
        model=model_adi,
        google_api_key=ayarlar.google_api_key,
        temperature=0,
        max_retries=MAKS_TEKRAR,
        timeout=ayarlar.gemini_zaman_asimi_sn,
        callbacks=[SureOlcer(is_adi, model_adi, ayar_adi)],
        **({"thinking_level": dusunme} if dusunme else {}),
    )


def yedekli_zincir(
    katman: Katman, is_adi: str, zincir_kur: Callable[[ChatGoogleGenerativeAI], Runnable]
) -> Runnable:
    """Aynı zinciri katmanın ana ve yedek modeliyle kurup birbirine bağlar.

    `zincir_kur` bir model alır ve o modelle çalışan zinciri döner — böylece
    yapılandırılmış çıktı da, düz metin de aynı yedekleme desenini kullanıyor.
    `is_adi` log satırlarında işi ayırt etmek için (örn. "dogrulama_rubrik").
    Yedek de başarısız olursa hata çağırana kadar çıkar.
    """
    ana, yedek = katman_modelleri(katman)
    ana_ayari, yedek_ayari = AYAR_ADLARI[katman]
    # Düşünme seviyesi yalnızca hızlı katmanda ayarlanabiliyor; güçlü katman
    # (gerekçe, rubrik) modelin varsayılanıyla düşünür.
    dusunme = get_settings().gemini_hizli_dusunme if katman == "hizli" else None
    return zincir_kur(model(ana, is_adi, ana_ayari, dusunme)).with_fallbacks(
        [zincir_kur(model(yedek, is_adi, yedek_ayari, dusunme))],
        exceptions_to_handle=YEDEGE_DUSUREN_HATALAR,
    )


# --- Açılışta model adı kontrolü -------------------------------------------

MODELLER_URL = "https://generativelanguage.googleapis.com/v1beta/models"
# Açılışı yavaşlatmasın diye kısa; kontrol zaten arka planda çalışıyor.
ACILIS_KONTROL_ZAMAN_ASIMI_SN = 5.0


def model_ayarlari() -> dict[str, str]:
    """.env değişkeni → gösterdiği model adı (dört model)."""
    sonuc: dict[str, str] = {}
    for katman, (ana_ayari, yedek_ayari) in AYAR_ADLARI.items():
        ana, yedek = katman_modelleri(katman)
        sonuc[ana_ayari] = ana
        sonuc[yedek_ayari] = yedek
    return sonuc


async def _mevcut_modeller(istemci: httpx.AsyncClient, anahtar: str) -> set[str]:
    """Anahtarın gördüğü model adları (`models/` öneki atılmış), sayfalar birleşik."""
    adlar: set[str] = set()
    sayfa: str | None = None
    while True:
        parametreler = {"pageSize": 1000, **({"pageToken": sayfa} if sayfa else {})}
        # Anahtar başlıkta: httpx istek URL'sini INFO'da log'a yazıyor, sorgu
        # parametresi olarak gitse anahtar günlüğe düşerdi.
        yanit = await istemci.get(
            MODELLER_URL, params=parametreler, headers={"x-goog-api-key": anahtar}
        )
        yanit.raise_for_status()
        govde = yanit.json()
        adlar.update(m["name"].removeprefix("models/") for m in govde.get("models", []))
        sayfa = govde.get("nextPageToken")
        if not sayfa:
            return adlar


async def model_adlarini_dogrula(
    istemci: httpx.AsyncClient | None = None,
) -> list[tuple[str, str]]:
    """.env'deki dört model adını models.list ile karşılaştırır; eksikleri uyarır.

    Uygulamayı DURDURMAZ: bulunamayan model çağrıldığında zaten yedeğe
    düşülüyor (404 `YEDEGE_DUSUREN_HATALAR`'da). Amaç yanlış yazılmış ya da
    kaldırılmış bir model adını ilk istekten önce, açılış log'unda göstermek.

    Kontrolün kendisi başarısız olursa (ağ yok, anahtar yok, beklenmeyen
    yanıt) sessizce geçilir — açılışı engellememeli.

    Sınır: bir model listede görünüp çağrıda 404 dönebiliyor (gemini-2.5-pro
    "yeni kullanıcılara kapalı"). O durumu bu kontrol değil, çağrı anındaki
    `MODEL KULLANILAMIYOR` log'u yakalıyor.
    """
    anahtar = get_settings().google_api_key
    if not anahtar:
        return []
    try:
        if istemci is None:
            async with httpx.AsyncClient(timeout=ACILIS_KONTROL_ZAMAN_ASIMI_SN) as yeni:
                mevcutlar = await _mevcut_modeller(yeni, anahtar)
        else:
            mevcutlar = await _mevcut_modeller(istemci, anahtar)
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        logger.debug("Açılış model kontrolü yapılamadı; atlanıyor", exc_info=True)
        return []

    eksikler = [(ayar, ad) for ayar, ad in model_ayarlari().items() if ad not in mevcutlar]
    for ayar, ad in eksikler:
        sonucu = (
            "ana model arızalanırsa bu katmanın yedeği de çalışmayacak"
            if ayar.endswith("_YEDEK_MODEL")
            else "bu katmanın her çağrısı yedek modele düşecek"
        )
        logger.warning(
            "Model bulunamadı: %s=%s sağlayıcının model listesinde yok; %s. "
            ".env'de %s değerini kontrol et.",
            ayar,
            ad,
            sonucu,
            ayar,
        )
    return eksikler
