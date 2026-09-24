"""Keşif ve Tanımlama ajanlarının paylaştığı sohbet motoru.

docs/agent-specs.md § 2: "Keşif Ajanı ile aynı sohbet motorunu paylaşır
(ayrı yazılmaz), sadece soru seti farklıdır."

Motorun bildiği üç şey var:
  1. Grafik iskeleti — açılış → yapılandırılmış çıkarım → karar düğümü.
  2. Taslak birleştirme — skaler alan üzerine yazar, liste alanı tekrarsız
     ekler, boş gelen çıkarım eski değeri SİLMEZ.
  3. Yedek modele düşen LLM zinciri (ücretsiz katman kotası model başına).

Ajana özel olan her şey (`AjanTanimi`) dışarıdan verilir: açılış sorusu,
sistem talimatı, çıkarım şeması, zorunlu alanlar. Bir ajanın kendine has bir
dalı varsa (Keşif'in "hiç projem yok" fallback zinciri gibi) `ek_dal` ile
eklenir — motorun içinde ajana özel dal yok.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import GoogleRateLimitError
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel

from app.core.config import get_settings

# Eksik alan için en fazla kaç tur takip sorusu sorulur (agent-specs.md § 1.2;
# Tanımlama da aynı sınırı kullanır).
MAKS_TAKIP_TURU = 2


class SohbetDurumu(TypedDict, total=False):
    """Her ajanın paylaştığı durum. Ajanlar bunu genişletebilir."""

    mesajlar: Annotated[list[AnyMessage], add_messages]
    taslak: dict[str, Any]
    takip_turu: int
    sonraki_soru: str | None
    taslak_hazir: bool
    # Son turun çıkarımından karar düğümüne taşınan takip sorusu önerisi
    son_takip_sorusu: str | None


@dataclass(frozen=True)
class AjanTanimi:
    """Bir sohbet ajanının motora verdiği her şey."""

    ad: str
    acilis_sorusu: str
    sistem_talimati: str
    cikarim_semasi: type[BaseModel]
    # Üzerine yazılan alanlar (tek değer) ve tekrarsız eklenen liste alanları
    skaler_alanlar: tuple[str, ...] = ()
    liste_alanlari: tuple[str, ...] = ()
    # (alan adı, tekilleştirme anahtarı) — örn. ("somut_ciktilar", "baslik")
    nesne_listeleri: tuple[tuple[str, str], ...] = ()
    zorunlu_alanlar: tuple[str, ...] = ()
    # LLM takip sorusu üretmezse kullanılan sabit metinler
    yedek_sorular: Mapping[str, str] = field(default_factory=dict)
    # Takip soruları bittikten sonra çalışan, ajana özel dal. Bir durum
    # güncellemesi dönerse sohbet devam eder, None dönerse taslak kapanır.
    ek_dal: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None
    # Çıkarımdan taslağa değil, doğrudan duruma yazılacak bayraklar
    # (Keşif'te "kullanıcı projesi olmadığını söyledi" gibi).
    ek_cikarim_alanlari: Callable[[BaseModel], dict[str, Any]] | None = None
    # Taslağı kapatmadan önceki son rötuş (örn. "potansiyel" etiketi)
    tamamla: Callable[[dict[str, Any]], dict[str, Any]] | None = None


class HizSinirHatasi(RuntimeError):
    """LLM sağlayıcısı kotayı doldurdu (Gemini ücretsiz katman)."""


def _llm(model_adi: str) -> ChatGoogleGenerativeAI:
    ayarlar = get_settings()
    if not ayarlar.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY tanımlı değil (.env)")
    return ChatGoogleGenerativeAI(
        model=model_adi,
        google_api_key=ayarlar.google_api_key,
        temperature=0,
    )


def cikarim_zinciri(sema: type[BaseModel]) -> Runnable:
    """Aynı prompt ve şemayla çalışan iki modelden oluşan zincir.

    Gemini ücretsiz katmanında günlük kota model başına ayrı işliyor; ana
    modelin kotası dolunca (429/RESOURCE_EXHAUSTED) aynı çağrı yedek modele
    düşer. Yedeğin de kotası dolarsa hata çağırana kadar çıkar ve kullanıcı
    429 görür — sohbet checkpointer'da durduğu için kaybolmaz.

    Önbellek ajanın kendi sarmalayıcısında (her ajan kendi zincirini tutar).
    """
    ayarlar = get_settings()
    ana = _llm(ayarlar.gemini_model).with_structured_output(sema)
    yedek = _llm(ayarlar.gemini_yedek_model).with_structured_output(sema)
    return ana.with_fallbacks([yedek], exceptions_to_handle=(GoogleRateLimitError,))


def bos_taslak(tanim: AjanTanimi) -> dict[str, Any]:
    taslak: dict[str, Any] = {alan: None for alan in tanim.skaler_alanlar}
    for alan in tanim.liste_alanlari:
        taslak[alan] = []
    for alan, _ in tanim.nesne_listeleri:
        taslak[alan] = []
    return taslak


def eksik_alanlar(tanim: AjanTanimi, taslak: dict[str, Any]) -> list[str]:
    return [alan for alan in tanim.zorunlu_alanlar if not taslak.get(alan)]


def birlestir(tanim: AjanTanimi, taslak: dict[str, Any], cikarim: BaseModel) -> dict[str, Any]:
    """Yeni çıkarımı mevcut taslağa ekler — boş gelen alan eskisini silmez."""
    yeni = dict(taslak)

    for alan in tanim.skaler_alanlar:
        deger = getattr(cikarim, alan, None)
        if deger:
            yeni[alan] = deger

    for alan in tanim.liste_alanlari:
        mevcut = list(yeni.get(alan) or [])
        for deger in getattr(cikarim, alan, []) or []:
            if deger and deger not in mevcut:
                mevcut.append(deger)
        yeni[alan] = mevcut

    for alan, anahtar in tanim.nesne_listeleri:
        nesneler = list(yeni.get(alan) or [])
        gorulen = {n[anahtar].casefold() for n in nesneler}
        for nesne in getattr(cikarim, alan, []) or []:
            deger = getattr(nesne, anahtar)
            if deger.casefold() not in gorulen:
                nesneler.append(nesne.model_dump())
                gorulen.add(deger.casefold())
        yeni[alan] = nesneler

    return yeni


# --- Grafik düğümleri ------------------------------------------------------


def _acilis_dugumu(tanim: AjanTanimi, ek_baslangic: Mapping[str, Any]):
    async def acilis(durum: dict[str, Any]) -> dict[str, Any]:
        """Sohbeti açar. LLM çağrısı yok — açılış sorusu sabit."""
        return {
            "mesajlar": [AIMessage(content=tanim.acilis_sorusu)],
            "taslak": bos_taslak(tanim),
            "takip_turu": 0,
            "sonraki_soru": tanim.acilis_sorusu,
            "taslak_hazir": False,
            **ek_baslangic,
        }

    return acilis


def _cikar_dugumu(tanim: AjanTanimi, zincir_uret: Callable[[], Runnable]):
    async def cikar(durum: dict[str, Any]) -> dict[str, Any]:
        """Konuşmanın tamamını yapılandırılmış alanlara döker (function calling)."""
        try:
            cikarim = await zincir_uret().ainvoke(
                [SystemMessage(content=tanim.sistem_talimati), *durum["mesajlar"]]
            )
        except Exception as hata:
            # Ücretsiz katmanda günlük/dakikalık kota dolabiliyor. Bunu 500
            # olarak değil, ne olduğunu söyleyen ayrı bir hata olarak taşı.
            metin = str(hata)
            if "RESOURCE_EXHAUSTED" in metin or "429" in metin:
                raise HizSinirHatasi(metin) from hata
            raise

        return {
            "taslak": birlestir(tanim, durum.get("taslak") or bos_taslak(tanim), cikarim),
            "son_takip_sorusu": getattr(cikarim, "takip_sorusu", None),
            **(tanim.ek_cikarim_alanlari(cikarim) if tanim.ek_cikarim_alanlari else {}),
        }

    return cikar


async def karar(tanim: AjanTanimi, durum: dict[str, Any]) -> dict[str, Any]:
    """Takip sorusu mu, ajana özel dal mı, yoksa taslak mı — tek karar noktası."""
    taslak = durum["taslak"]
    eksikler = eksik_alanlar(tanim, taslak)
    takip_turu = durum.get("takip_turu", 0)

    # 1) Zorunlu alan eksikse, 2 turu aşmadan takip sorusu sor.
    if eksikler and takip_turu < MAKS_TAKIP_TURU:
        soru = durum.get("son_takip_sorusu") or tanim.yedek_sorular[eksikler[0]]
        return {
            "mesajlar": [AIMessage(content=soru)],
            "takip_turu": takip_turu + 1,
            "sonraki_soru": soru,
            "taslak_hazir": False,
        }

    # 2) Ajana özel dal (Keşif'te "hiç projem yok" zinciri; Tanımlama'da yok).
    if tanim.ek_dal is not None:
        ek = tanim.ek_dal(durum)
        if ek is not None:
            return ek

    # 3) Taslak hazır.
    son_taslak = tanim.tamamla(taslak) if tanim.tamamla else dict(taslak)
    return {"taslak": son_taslak, "sonraki_soru": None, "taslak_hazir": True}


def _karar_dugumu(tanim: AjanTanimi):
    async def karar_dugumu(durum: dict[str, Any]) -> dict[str, Any]:
        return await karar(tanim, durum)

    return karar_dugumu


def _baslangic_yonu(durum: dict[str, Any]) -> Literal["acilis", "cikar"]:
    """İlk çağrıda açılış sorusu, sonrakilerde çıkarım."""
    return "cikar" if durum.get("mesajlar") and durum.get("taslak") is not None else "acilis"


def grafik_derle(
    tanim: AjanTanimi,
    durum_semasi: type,
    checkpointer: BaseCheckpointSaver,
    zincir_uret: Callable[[], Runnable],
    ek_baslangic: Mapping[str, Any] | None = None,
):
    """Ajanın grafiğini derler. Checkpointer uygulama ömrü boyunca paylaşılır."""
    grafik = StateGraph(durum_semasi)
    grafik.add_node("acilis", _acilis_dugumu(tanim, ek_baslangic or {}))
    grafik.add_node("cikar", _cikar_dugumu(tanim, zincir_uret))
    grafik.add_node("karar", _karar_dugumu(tanim))

    grafik.add_conditional_edges(START, _baslangic_yonu, {"acilis": "acilis", "cikar": "cikar"})
    grafik.add_edge("acilis", END)
    grafik.add_edge("cikar", "karar")
    grafik.add_edge("karar", END)

    return grafik.compile(checkpointer=checkpointer)


def kullanici_mesaji(metin: str) -> HumanMessage:
    return HumanMessage(content=metin)


def zorunlu_alanlari_doldur(
    taslak: dict[str, Any],
    zorunlu: Sequence[str],
    metin_alanlari: Sequence[str],
    yer_tutucu: str = "belirtilmedi",
) -> dict[str, Any]:
    """Takip turları bitince boş kalan zorunlu alanları doldurur."""
    son = dict(taslak)
    for alan in zorunlu:
        if not son.get(alan):
            son[alan] = yer_tutucu if alan in metin_alanlari else []
    return son
