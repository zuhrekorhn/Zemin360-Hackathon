"""Keşif Ajanı — gençle sohbet eder, konuşmayı yetenek kartı taslağına çevirir.

Grafik iskeleti, taslak birleştirme ve LLM zinciri ortak motorda
(app/agents/sohbet_motoru.py). Burada kalan her şey Keşif'e özel.

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
from typing import Any, Literal

from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, Field

from app.agents import sohbet_motoru as motor
from app.agents.sohbet_motoru import (  # noqa: F401 — dışarıya tek kapı burası
    MAKS_TAKIP_TURU,
    HizSinirHatasi,
    SohbetDurumu,
    kullanici_mesaji,
)

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
  Her çıktı için iki şeyi de öğrenmeye çalış, ama tek seferde tek soru sor:
  * olculebilir_sonuc: sayıyla anlatılabilen bir sonuç ("kaç kişi kullandı?",
    "ne kadar zaman kazandırdı?", "kaç kayıt işliyor?").
  * kendi_rolu: ekip işiyse kullanıcının kendi payı ("hangi kısmını sen yaptın?").
  Kullanıcı bilmiyorsa ya da yoksa ISRAR ETME, boş bırak. Sayı UYDURMA.

Aynı işten ikinci kez bahsedilirse YENİ bir çıktı açma; aynı başlıkla yeniden
döndür, eksik alanları doldur.
"""

YEDEK_SORULAR = {
    "rol_alani": "Kendini hangi alanda görüyorsun? Kısaca nasıl tanımlarsın?",
    "deneyim_seviyesi": "Bu alanda ne kadar zamandır uğraşıyorsun?",
    "sektor_ilgi_alani": "Hangi sektörlerde çalışmak ilgini çeker?",
    "araclar_teknolojiler": "Hangi araçları ya da yöntemleri kullanıyorsun?",
}


class SomutCiktiTaslak(BaseModel):
    """Bir somut çıktı.

    `olculebilir_sonuc` ve `kendi_rolu` Doğrulama Ajanı'nın rubriğiyle birebir
    hizalı (agent-specs.md § 4: "ölçülebilir sonuç" ve "rol netliği"). Keşif
    bunları sormazsa rubrik puanlayacak bir şey bulamıyor — gerçek bir kart
    bu yüzden 0/3 ve 1/3 almıştı.
    """

    baslik: str = Field(description="Kısa başlık, örn. 'Mahalle kütüphanesi ödünç takip sistemi'")
    aciklama: str | None = Field(
        default=None,
        description="Ne yaptığı ve ortaya ne çıktığı, kullanıcının anlattığı kadarıyla",
    )
    olculebilir_sonuc: str | None = Field(
        default=None,
        description=(
            "Sayı, oran ya da süre içeren sonuç — kullanıcı söylediyse. "
            "Örn. '400 kitap ve 120 üye takip ediliyor'. Uydurma."
        ),
    )
    kendi_rolu: str | None = Field(
        default=None,
        description=(
            "Kullanıcının bu işteki kendi payı, kendi ifadesiyle. "
            "Örn. 'backend'i ben yazdım, tasarımı arkadaşım yaptı'. Uydurma."
        ),
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


class KesifDurumu(SohbetDurumu, total=False):
    """Ortak duruma Keşif'in fallback zinciri için iki alan ekler."""

    fallback_indeksi: int
    cikti_yok_dedi: bool


def _fallback_dali(durum: dict[str, Any]) -> dict[str, Any] | None:
    """Somut çıktı yoksa fallback zinciri (okul ödevi → gönüllü iş).

    Zincir bitmişse None döner ve taslak kapanır.
    """
    fallback_indeksi = durum.get("fallback_indeksi", 0)
    if durum["taslak"].get("somut_ciktilar") or fallback_indeksi >= len(FALLBACK_SORULARI):
        return None

    soru = FALLBACK_SORULARI[fallback_indeksi]
    return {
        "mesajlar": [AIMessage(content=soru)],
        "fallback_indeksi": fallback_indeksi + 1,
        "sonraki_soru": soru,
        "taslak_hazir": False,
    }


def _cikti_eksikleri(taslak: dict[str, Any]) -> list[tuple[str, str]]:
    """Çıktı başına eksik olan ölçüt/rol bilgisi için takip soruları.

    Zorunlu alan değiller: kullanıcı bilmiyorsa kart yine kurulur. Ama
    sorulmazsa Doğrulama Ajanı'nın iki bileşeni kesin düşük kalıyor.
    """
    eksikler: list[tuple[str, str]] = []
    for cikti in taslak.get("somut_ciktilar") or []:
        baslik = cikti.get("baslik") or "bu iş"
        if not cikti.get("olculebilir_sonuc"):
            eksikler.append(
                (
                    f"olcut:{baslik}",
                    f"“{baslik}” için sonucu sayıyla anlatabilir misin? "
                    "Kaç kişi kullandı, ne kadar zaman kazandırdı gibi.",
                )
            )
        if not cikti.get("kendi_rolu"):
            eksikler.append(
                (
                    f"rol:{baslik}",
                    f"“{baslik}” işinde senin payın neydi? Tek başına mıydın, "
                    "ekipçe miydi — hangi kısmı sen yaptın?",
                )
            )
    return eksikler


def _cikti_aciklamasi(cikti: dict[str, Any]) -> str | None:
    """Açıklama, ölçüt ve rol bilgisini tek metinde toplar.

    Doğrulama Ajanı yalnızca `aciklama`'yı okuyor; bilgiyi ayrı alanlarda
    bırakmak rubriğe ulaşmasını engellerdi.
    """
    parcalar = [
        cikti.get("aciklama"),
        cikti.get("olculebilir_sonuc"),
        cikti.get("kendi_rolu"),
    ]
    metin = " ".join(p.strip() for p in parcalar if p and p.strip())
    return metin or None


def _tamamla(taslak: dict[str, Any]) -> dict[str, Any]:
    """Çıktısı olmayan kart "potansiyel" etiketiyle çıkar — Doğrulama Ajanı'nı
    atlayıp doğrudan Eşleştirme'ye gider (agent-specs.md § 1.4)."""
    son = dict(taslak)
    son["somut_ciktilar"] = [
        {**cikti, "aciklama": _cikti_aciklamasi(cikti)} for cikti in son.get("somut_ciktilar") or []
    ]
    if not son["somut_ciktilar"]:
        son["deneyim_seviyesi"] = "potansiyel"
    return motor.zorunlu_alanlari_doldur(
        son, ZORUNLU_ALANLAR, metin_alanlari=("rol_alani", "deneyim_seviyesi")
    )


KESIF = motor.AjanTanimi(
    ad="kesif",
    acilis_sorusu=ACILIS_SORUSU,
    sistem_talimati=SISTEM_TALIMATI,
    cikarim_semasi=TaslakCikarimi,
    skaler_alanlar=("rol_alani", "deneyim_seviyesi"),
    liste_alanlari=("sektor_ilgi_alani", "araclar_teknolojiler"),
    nesne_listeleri=(("somut_ciktilar", "baslik"),),
    zorunlu_alanlar=ZORUNLU_ALANLAR,
    yedek_sorular=YEDEK_SORULAR,
    ek_eksikler=_cikti_eksikleri,
    ek_dal=_fallback_dali,
    ek_cikarim_alanlari=lambda cikarim: {"cikti_yok_dedi": cikarim.somut_cikti_yok_dedi},
    tamamla=_tamamla,
)


@lru_cache
def _cikarim_zinciri() -> Runnable:
    return motor.cikarim_zinciri(TaslakCikarimi)


def bos_taslak() -> dict[str, Any]:
    return motor.bos_taslak(KESIF)


def _birlestir(taslak: dict[str, Any], cikarim: TaslakCikarimi) -> dict[str, Any]:
    return motor.birlestir(KESIF, taslak, cikarim)


async def _karar(durum: dict[str, Any]) -> dict[str, Any]:
    return await motor.karar(KESIF, durum)


def grafik_derle(checkpointer: BaseCheckpointSaver):
    return motor.grafik_derle(
        KESIF,
        KesifDurumu,
        checkpointer,
        _cikarim_zinciri,
        ek_baslangic={"fallback_indeksi": 0},
    )
