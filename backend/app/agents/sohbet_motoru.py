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
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel

from app.core.llm import HizSinirHatasi, llm_hatasini_cevir, model, yedekli_zincir
from app.core.metin import sade_anahtar

__all__ = ["HizSinirHatasi"]

# Eksik alan için en fazla kaç tur takip sorusu sorulur (agent-specs.md § 1.2;
# Tanımlama da aynı sınırı kullanır).
MAKS_TAKIP_TURU = 2
# Zorunlu alanlar için ayrı ve daha yüksek bir tavan: eksik alanla kart
# kapatmak, sohbeti bir tur uzatmaktan kötü (boş "sektör ilgisi" eşleştirmede
# doğrudan skora yansıyor). Yine de sonsuz döngü olmasın diye bir sınır var;
# tavana gelinirse alanlar yer tutucuyla doldurulup kart kapanıyor.
MAKS_ZORUNLU_TURU = 6


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
    # Zorunlu alan eksikken kaç tur soru sorulabilir (ajana göre değişir).
    maks_zorunlu_turu: int = MAKS_ZORUNLU_TURU
    # Ajana özel eksikler: (anahtar, soru) listesi. Zorunlu alanlar
    # tamamlandıktan SONRA sorulur — örn. Keşif'te her çıktının sayısal
    # sonucu ve kullanıcının kendi payı.
    ek_eksikler: Callable[[dict[str, Any]], list[tuple[str, str]]] | None = None
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


def cikarim_zinciri(sema: type[BaseModel]) -> Runnable:
    """Aynı prompt ve şemayla çalışan iki modelden oluşan zincir.

    Gemini ücretsiz katmanında günlük kota model başına ayrı işliyor; ana
    modelin kotası dolunca (429/RESOURCE_EXHAUSTED) aynı çağrı yedek modele
    düşer. Yedeğin de kotası dolarsa hata çağırana kadar çıkar ve kullanıcı
    429 görür — sohbet checkpointer'da durduğu için kaybolmaz.

    Önbellek ajanın kendi sarmalayıcısında (her ajan kendi zincirini tutar).
    """
    return yedekli_zincir(lambda model_adi: model(model_adi).with_structured_output(sema))


def bos_taslak(tanim: AjanTanimi) -> dict[str, Any]:
    taslak: dict[str, Any] = {alan: None for alan in tanim.skaler_alanlar}
    for alan in tanim.liste_alanlari:
        taslak[alan] = []
    for alan, _ in tanim.nesne_listeleri:
        taslak[alan] = []
    return taslak


def eksik_alanlar(tanim: AjanTanimi, taslak: dict[str, Any]) -> list[str]:
    return [alan for alan in tanim.zorunlu_alanlar if not taslak.get(alan)]


def _nesneleri_birlestir(
    nesneler: list[dict[str, Any]], gelenler: Sequence[Any], anahtar: str
) -> list[dict[str, Any]]:
    """Aynı işi anlatan kayıtları tek kayıtta toplar.

    Kullanıcı projeden ikinci kez bahsettiğinde ("Team To Do" / "Team ToDo")
    ajan yeni bir çıktı açıyordu; biri linksiz, diğeri linkli iki satır
    çıkıyordu. Başlık noktalama ve büyük/küçük harf farkından arındırılıp
    karşılaştırılıyor, eşleşen kayıtların BOŞ alanları yeni bilgiyle
    dolduruluyor — dolu bir alan ezilmiyor, ilk anlatılan korunuyor.
    """
    dizin = {sade_anahtar(nesne[anahtar]): sira for sira, nesne in enumerate(nesneler)}

    for gelen in gelenler:
        veri = gelen.model_dump()
        gelen_anahtar = sade_anahtar(veri[anahtar])
        sira = dizin.get(gelen_anahtar)
        if sira is None:
            dizin[gelen_anahtar] = len(nesneler)
            nesneler.append(veri)
            continue
        mevcut = nesneler[sira]
        for alan_adi, deger in veri.items():
            if deger and not mevcut.get(alan_adi):
                mevcut[alan_adi] = deger

    return nesneler


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
        yeni[alan] = _nesneleri_birlestir(
            list(yeni.get(alan) or []), getattr(cikarim, alan, []) or [], anahtar
        )

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
            # Ücretsiz katmanda kota dolabiliyor, sağlayıcı da anlık 5xx
            # verebiliyor. İkisini de 500 olarak değil, ne olduğunu söyleyen
            # ayrı hatalar olarak taşı.
            cevrilmis = llm_hatasini_cevir(hata)
            raise cevrilmis from hata

        return {
            "taslak": birlestir(tanim, durum.get("taslak") or bos_taslak(tanim), cikarim),
            "son_takip_sorusu": getattr(cikarim, "takip_sorusu", None),
            **(tanim.ek_cikarim_alanlari(cikarim) if tanim.ek_cikarim_alanlari else {}),
        }

    return cikar


def _soru_durumu(soru: str, takip_turu: int) -> dict[str, Any]:
    return {
        "mesajlar": [AIMessage(content=soru)],
        "takip_turu": takip_turu + 1,
        "sonraki_soru": soru,
        "taslak_hazir": False,
    }


async def karar(tanim: AjanTanimi, durum: dict[str, Any]) -> dict[str, Any]:
    """Takip sorusu mu, ajana özel dal mı, yoksa taslak mı — tek karar noktası."""
    taslak = durum["taslak"]
    eksikler = eksik_alanlar(tanim, taslak)
    takip_turu = durum.get("takip_turu", 0)

    # 1) Zorunlu alan eksikse sormaya devam et. Kartı eksik kapatmak son
    #    çare; tavan yalnızca sonsuz döngüyü engelliyor.
    if eksikler and takip_turu < tanim.maks_zorunlu_turu:
        soru = durum.get("son_takip_sorusu") or tanim.yedek_sorular[eksikler[0]]
        return _soru_durumu(soru, takip_turu)

    # 2) Ajana özel eksikler (Keşif'te çıktı başına ölçülebilir sonuç ve rol).
    #    Zorunlu alanlardan sonra ve daha kısa bir tavanla soruluyor: bunlar
    #    kartı güçlendirir ama olmadan da kart kurulabilir.
    if tanim.ek_eksikler is not None and takip_turu < MAKS_TAKIP_TURU:
        ekler = tanim.ek_eksikler(taslak)
        if ekler:
            return _soru_durumu(ekler[0][1], takip_turu)

    # 3) Ajana özel dal (Keşif'te "hiç projem yok" zinciri; Tanımlama'da yok).
    if tanim.ek_dal is not None:
        ek = tanim.ek_dal(durum)
        if ek is not None:
            return ek

    # 4) Taslak hazır.
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
