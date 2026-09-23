"""Keşif Ajanı — gençle sohbet eder, konuşmayı yetenek kartı taslağına çevirir.

docs/agent-specs.md § 1. Sınırlar oradan geliyor:
  - Boş alan kalırsa EN FAZLA 2 tur takip sorusu (madde 2).
  - "Hiç projem yok" → fallback soru zinciri, hâlâ yoksa deneyim_seviyesi
    "potansiyel" ile kart oluşur (madde 4). Bu iki sınır ayrı sayılır:
    eksik alan takibi 2 tur, fallback zinciri 2 soru → açılışla birlikte en
    fazla 5 soru, yani spec'teki "5-7 soru" aralığında.
  - Kart taslağı kullanıcıya gösterilir, kaydetme onaydan sonra olur (madde 3).

Doğrulama ve puanlama bu ajanın işi değil — kanıt linki sadece toplanır,
değerlendirilmez.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.core.config import get_settings

ACILIS_SORUSU = (
    "Merhaba! Seni tanımak istiyorum. Son bir yılda bitirdiğin, sonucunu "
    "görebildiğin bir iş anlat — okuldan, işten ya da gönüllü bir işten olabilir. "
    "Ne yaptın, ne ortaya çıktı?"
)

# "Hiç projem yok" dalında sırayla sorulacak sorular (agent-specs.md § 1.4).
FALLBACK_SORULARI = (
    "Sorun değil, illa bir iş deneyimi olması gerekmiyor. Okulda üzerinde "
    "çalıştığın bir ödev, bitirme projesi ya da ders dışı bir şey var mı? "
    "Küçük de olsa olur.",
    "Peki gönüllü olarak yaptığın bir şey — bir dernekte, okulda bir kulüpte, "
    "mahallende? Ya da kendi kendine öğrenirken yaptığın bir deneme?",
)

ZORUNLU_ALANLAR = ("rol_alani", "deneyim_seviyesi", "sektor_ilgi_alani", "araclar_teknolojiler")

MAKS_TAKIP_TURU = 2

SISTEM_TALIMATI = """Sen Zemin360'ın Keşif Ajanı'sın. Genç bir kullanıcıyla sohbet ediyorsun.

Görevin: konuşmadan yetenek kartı alanlarını çıkarmak.
- Sektör-nötr ol: yazılımcı da, pazarlamacı da, tasarımcı da aynı kartı doldurabilir.
- Kullanıcının söylemediği bir şeyi UYDURMA. Emin olmadığın alanı boş bırak.
- Doğruluk kontrolü yapma, puanlama yapma, kanıt değerlendirme. Bu senin işin değil.
- Türkçe, sade ve sıcak konuş; tek seferde tek soru sor.

Alanlar:
- rol_alani: kullanıcının kendini konumlandırdığı alan ("mobil geliştirici",
  "sosyal medya içerik üreticisi" gibi).
- deneyim_seviyesi: potansiyel | baslangic | orta | ileri.
  Somut bir çıktısı yoksa "potansiyel".
- sektor_ilgi_alani: ilgilendiği sektörler.
- araclar_teknolojiler: kullandığı araç/teknoloji/yöntemler (yazılım olmak zorunda değil).
- somut_ciktilar: bitirdiği, sonucu olan işler. Kanıt linkini söylediyse ekle.
"""


class SomutCiktiTaslak(BaseModel):
    baslik: str = Field(description="Kısa başlık, örn. 'Mahalle kütüphanesi ödünç takip sistemi'")
    aciklama: str | None = Field(
        default=None,
        description="Ne yaptığı ve ortaya ne çıktığı, kullanıcının anlattığı kadarıyla",
    )
    kanit_linki: str | None = Field(default=None, description="Kullanıcı bir link verdiyse")


class TaslakCikarimi(BaseModel):
    """LLM'in her turda döndürdüğü yapılandırılmış çıkarım.

    Serbest metin parse edilmiyor; Gemini'nin structured output'u kullanılıyor.
    Bilinmeyen alanlar None/boş döner ve mevcut taslağın üzerine YAZMAZ.
    """

    rol_alani: str | None = None
    deneyim_seviyesi: Literal["potansiyel", "baslangic", "orta", "ileri"] | None = None
    sektor_ilgi_alani: list[str] = Field(default_factory=list)
    araclar_teknolojiler: list[str] = Field(default_factory=list)
    somut_ciktilar: list[SomutCiktiTaslak] = Field(default_factory=list)
    somut_cikti_yok_dedi: bool = Field(
        default=False,
        description="Kullanıcı bu turda anlatacak bir işi/projesi olmadığını söylediyse True",
    )
    takip_sorusu: str | None = Field(
        default=None,
        description="Eksik kalan alanlar için sorulabilecek tek bir doğal takip sorusu",
    )


class KesifDurumu(TypedDict, total=False):
    mesajlar: Annotated[list[AnyMessage], add_messages]
    taslak: dict[str, Any]
    takip_turu: int
    fallback_indeksi: int
    sonraki_soru: str | None
    taslak_hazir: bool
    # Son turun çıkarımından karar düğümüne taşınan iki bilgi
    son_takip_sorusu: str | None
    cikti_yok_dedi: bool


@lru_cache
def _llm() -> ChatGoogleGenerativeAI:
    ayarlar = get_settings()
    if not ayarlar.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY tanımlı değil (.env)")
    return ChatGoogleGenerativeAI(
        model=ayarlar.gemini_model,
        google_api_key=ayarlar.google_api_key,
        temperature=0,
    )


def bos_taslak() -> dict[str, Any]:
    return {
        "rol_alani": None,
        "deneyim_seviyesi": None,
        "sektor_ilgi_alani": [],
        "araclar_teknolojiler": [],
        "somut_ciktilar": [],
    }


def _eksik_alanlar(taslak: dict[str, Any]) -> list[str]:
    return [alan for alan in ZORUNLU_ALANLAR if not taslak.get(alan)]


def _birlestir(taslak: dict[str, Any], cikarim: TaslakCikarimi) -> dict[str, Any]:
    """Yeni çıkarımı mevcut taslağa ekler — boş gelen alan eskisini silmez."""
    yeni = dict(taslak)

    for alan in ("rol_alani", "deneyim_seviyesi"):
        deger = getattr(cikarim, alan)
        if deger:
            yeni[alan] = deger

    for alan in ("sektor_ilgi_alani", "araclar_teknolojiler"):
        mevcut = list(yeni.get(alan) or [])
        for deger in getattr(cikarim, alan):
            if deger and deger not in mevcut:
                mevcut.append(deger)
        yeni[alan] = mevcut

    ciktilar = list(yeni.get("somut_ciktilar") or [])
    mevcut_basliklar = {c["baslik"].casefold() for c in ciktilar}
    for cikti in cikarim.somut_ciktilar:
        if cikti.baslik.casefold() not in mevcut_basliklar:
            ciktilar.append(cikti.model_dump())
            mevcut_basliklar.add(cikti.baslik.casefold())
    yeni["somut_ciktilar"] = ciktilar

    return yeni


# --- Grafik düğümleri ------------------------------------------------------


async def _acilis(durum: KesifDurumu) -> KesifDurumu:
    """Sohbeti açar. LLM çağrısı yok — açılış sorusu sabit."""
    return {
        "mesajlar": [AIMessage(content=ACILIS_SORUSU)],
        "taslak": bos_taslak(),
        "takip_turu": 0,
        "fallback_indeksi": 0,
        "sonraki_soru": ACILIS_SORUSU,
        "taslak_hazir": False,
    }


class HizSinirHatasi(RuntimeError):
    """LLM sağlayıcısı kotayı doldurdu (Gemini ücretsiz katman)."""


async def _cikar(durum: KesifDurumu) -> KesifDurumu:
    """Konuşmanın tamamını yapılandırılmış alanlara döker (function calling)."""
    zincir = _llm().with_structured_output(TaslakCikarimi)
    try:
        cikarim: TaslakCikarimi = await zincir.ainvoke(
            [SystemMessage(content=SISTEM_TALIMATI), *durum["mesajlar"]]
        )
    except Exception as hata:
        # Ücretsiz katmanda günlük/dakikalık kota dolabiliyor. Bunu 500 olarak
        # değil, ne olduğunu söyleyen ayrı bir hata olarak yukarı taşı.
        metin = str(hata)
        if "RESOURCE_EXHAUSTED" in metin or "429" in metin:
            raise HizSinirHatasi(metin) from hata
        raise

    taslak = _birlestir(durum.get("taslak") or bos_taslak(), cikarim)
    return {
        "taslak": taslak,
        "son_takip_sorusu": cikarim.takip_sorusu,
        "cikti_yok_dedi": cikarim.somut_cikti_yok_dedi,
    }


async def _karar(durum: KesifDurumu) -> KesifDurumu:
    """Takip sorusu mu, fallback sorusu mu, yoksa taslak mı — tek karar noktası."""
    taslak = durum["taslak"]
    eksikler = _eksik_alanlar(taslak)
    takip_turu = durum.get("takip_turu", 0)
    fallback_indeksi = durum.get("fallback_indeksi", 0)

    # 1) Zorunlu alan eksikse, 2 turu aşmadan takip sorusu sor.
    if eksikler and takip_turu < MAKS_TAKIP_TURU:
        soru = durum.get("son_takip_sorusu") or _yedek_soru(eksikler)
        return {
            "mesajlar": [AIMessage(content=soru)],
            "takip_turu": takip_turu + 1,
            "sonraki_soru": soru,
            "taslak_hazir": False,
        }

    # 2) Somut çıktı yoksa fallback zinciri (okul ödevi → gönüllü iş).
    if not taslak.get("somut_ciktilar") and fallback_indeksi < len(FALLBACK_SORULARI):
        soru = FALLBACK_SORULARI[fallback_indeksi]
        return {
            "mesajlar": [AIMessage(content=soru)],
            "fallback_indeksi": fallback_indeksi + 1,
            "sonraki_soru": soru,
            "taslak_hazir": False,
        }

    # 3) Taslak hazır. Çıktısı olmayan kart "potansiyel" etiketiyle çıkar —
    #    Doğrulama Ajanı'nı atlayıp doğrudan Eşleştirme'ye gider.
    son_taslak = dict(taslak)
    if not son_taslak.get("somut_ciktilar"):
        son_taslak["deneyim_seviyesi"] = "potansiyel"
    for alan in ZORUNLU_ALANLAR:
        if not son_taslak.get(alan):
            son_taslak[alan] = "belirtilmedi" if alan in ("rol_alani", "deneyim_seviyesi") else []

    return {
        "taslak": son_taslak,
        "sonraki_soru": None,
        "taslak_hazir": True,
    }


def _yedek_soru(eksikler: list[str]) -> str:
    """LLM takip sorusu üretmediyse kullanılan sabit metinler."""
    metinler = {
        "rol_alani": "Kendini hangi alanda görüyorsun? Kısaca nasıl tanımlarsın?",
        "deneyim_seviyesi": "Bu alanda ne kadar zamandır uğraşıyorsun?",
        "sektor_ilgi_alani": "Hangi sektörlerde çalışmak ilgini çeker?",
        "araclar_teknolojiler": "Hangi araçları ya da yöntemleri kullanıyorsun?",
    }
    return metinler[eksikler[0]]


def _baslangic_yonu(durum: KesifDurumu) -> Literal["acilis", "cikar"]:
    """İlk çağrıda açılış sorusu, sonrakilerde çıkarım."""
    return "cikar" if durum.get("mesajlar") and durum.get("taslak") is not None else "acilis"


def grafik_derle(checkpointer: BaseCheckpointSaver):
    """Keşif grafiğini derler. Checkpointer uygulama ömrü boyunca paylaşılır."""
    grafik = StateGraph(KesifDurumu)
    grafik.add_node("acilis", _acilis)
    grafik.add_node("cikar", _cikar)
    grafik.add_node("karar", _karar)

    grafik.add_conditional_edges(START, _baslangic_yonu, {"acilis": "acilis", "cikar": "cikar"})
    grafik.add_edge("acilis", END)
    grafik.add_edge("cikar", "karar")
    grafik.add_edge("karar", END)

    return grafik.compile(checkpointer=checkpointer)


def kullanici_mesaji(metin: str) -> HumanMessage:
    return HumanMessage(content=metin)
