"""Takip Ajanı — plan önerisi (docs/faz-c-takip.md § 4).

Sohbet ajanı değil: tek seferlik hesap (kartlar → istem → tek LLM çağrısı),
Eşleştirme gerekçesi ve Doğrulama rubriğiyle aynı desen. Ajan plan önerir;
onaylamaz, adım kapatmaz, iş birliğini bitirmez.

Çıktı kurala uymazsa (3-5 adım, 1-12 hafta, haftalar artan) düzeltme notuyla
bir kez yeniden istenir; yine uymazsa None döner ve plan boş kalır — taraflar
adımları elle ekleyebilir, çıkmaz sokak yok.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from app.core import calisma_modeli, musaitlik
from app.core.firma_karti import ISBIRLIGI_TURU_ETIKETLERI
from app.core.kullanici_dili import KULLANICI_DILI_KURALLARI
from app.core.llm import llm_hatasini_cevir, yedekli_zincir
from app.models.firma_karti import FirmaKarti
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.yetenek_karti import YetenekKarti

logger = logging.getLogger("zemin360.takip")

EN_AZ_ADIM = 3
EN_COK_ADIM = 5
EN_COK_HAFTA = 12


class AdimOnerisi(BaseModel):
    baslik: str = Field(description="Kısa, eylem bildiren başlık (en çok 8 kelime).")
    aciklama: str = Field(
        description="Ne olunca tamam sayılır: gözlemlenebilir, ölçülebilir tek cümle."
    )
    hafta: int = Field(description="Başlangıçtan itibaren kaçıncı haftanın sonunda biter (1-12).")


class PlanOnerisi(BaseModel):
    adimlar: list[AdimOnerisi] = Field(
        description="3-5 adım, zaman sırasıyla; son adım başarı kriterine bağlanır."
    )


SISTEM_TALIMATI = """Sen Zemin360'ın Takip Ajanı'sın. Bir kurum ile genç bir yetenek arasında
yeni açılan bir pilot iş birliği için 3-5 adımlık (milestone) bir plan ÖNERİYORSUN.
Planı iki taraf gözden geçirip düzenleyecek ve onaylayacak; sen karar vermiyorsun.

Kurallar:
- 3 ile 5 arasında adım yaz, zaman sırasıyla.
- Her adımın "hafta" değeri başlangıçtan itibaren kaçıncı haftanın sonunda bittiğidir:
  1 ile 12 arası, her adımda bir öncekinden BÜYÜK.
- Son adım, ihtiyaç kartındaki başarı kriterine doğrudan bağlanmalı.
- Her adımın açıklaması "ne olunca tamam sayılır" sorusunu tek cümleyle, gözlemlenebilir
  biçimde yanıtlamalı (ör. "Kayıt ekranı gönüllülerle denendi, 10 kayıt hatasız girildi").
- Kartlarda OLMAYAN bir sayı, araç, kişi ya da tarih UYDURMA. Başarı kriterindeki sayıları
  kullanabilirsin; başka sayı gerekiyorsa sayı yazma.
- Müsaitliği ve çalışma modelini hesaba kat: yarı zamanlı bir gence 2 haftada büyük iş verme.
- Teknik rol ve araç adlarını Türkçeleştirme (backend, API, FastAPI gibi yaygın adları koru).
- Düz, sade Türkçe; başlıklar kısa ve eylem bildiren."""
SISTEM_TALIMATI += KULLANICI_DILI_KURALLARI

PLAN_SABLONU = ChatPromptTemplate.from_messages(
    [
        ("system", SISTEM_TALIMATI),
        (
            "human",
            """İhtiyaç kartı (kurum: {kurum_adi})
- Problem: {problem_tanimi}
- Başarı kriteri: {basari_kriteri}
- Kısıtlar: {kisitlar}
- Müsaitlik tercihi: {musaitlik}
- Çalışma modeli: {calisma_modeli}

Yetenek kartı
- Rol: {rol_alani} ({deneyim_seviyesi})
- Araçlar: {araclar}
- Daha önce yaptığı somut işler: {ciktilar}
{ek_not}""",
        ),
    ]
)

DUZELTME_NOTU = (
    "\nÖNCEKİ DENEME KURALA UYMADI: tam olarak 3-5 adım yaz, her adımın haftası 1-12 arası "
    "ve bir öncekinden büyük olsun, başlık ve açıklama boş kalmasın."
)


def plan_girdileri(
    ihtiyac: IhtiyacKarti, kart: YetenekKarti, kurum_adi: str, ek_not: str = ""
) -> dict:
    """İstem girdileri. İletişim bilgisi (e-posta) hiç girmez."""
    return {
        "kurum_adi": kurum_adi,
        "problem_tanimi": ihtiyac.problem_tanimi,
        "basari_kriteri": ihtiyac.basari_kriteri or "(yazılmamış)",
        "kisitlar": ihtiyac.kisitlar or "(yok)",
        "musaitlik": musaitlik.ETIKETLER.get(ihtiyac.musaitlik_tercihi or "", "(belirtilmemiş)"),
        "calisma_modeli": calisma_modeli.ETIKETLER.get(
            ihtiyac.calisma_modeli or "", "(belirtilmemiş)"
        ),
        "rol_alani": kart.rol_alani,
        "deneyim_seviyesi": kart.deneyim_seviyesi,
        "araclar": ", ".join(kart.araclar_teknolojiler or []) or "(belirtilmemiş)",
        "ciktilar": "; ".join(c.baslik for c in kart.somut_ciktilar) or "(yok)",
        "ek_not": ek_not,
    }


def plan_gecerli_mi(oneri: PlanOnerisi) -> bool:
    """Kural: 3-5 adım, dolu başlık ve açıklama, hafta 1-12 ve kesin artan."""
    adimlar = oneri.adimlar
    if not EN_AZ_ADIM <= len(adimlar) <= EN_COK_ADIM:
        return False
    onceki = 0
    for adim in adimlar:
        if not adim.baslik.strip() or not adim.aciklama.strip():
            return False
        if not onceki < adim.hafta <= EN_COK_HAFTA:
            return False
        onceki = adim.hafta
    return True


def hedef_tarihi(baslangic: dt.date, hafta: int) -> dt.date:
    return baslangic + dt.timedelta(weeks=hafta)


@lru_cache
def _plan_zinciri() -> Runnable:
    # Güçlü katman: tek seferlik, nüans önemli (başarı kriterine bağlı,
    # ölçülebilir ara hedefler, uydurma yok).
    return yedekli_zincir(
        "guclu", "takip_plan", lambda m: PLAN_SABLONU | m.with_structured_output(PlanOnerisi)
    )


async def _plan_cagir(girdiler: dict) -> PlanOnerisi:
    try:
        return await _plan_zinciri().ainvoke(girdiler)
    except Exception as hata:
        raise llm_hatasini_cevir(hata) from hata


async def plan_oner(
    ihtiyac: IhtiyacKarti, kart: YetenekKarti, kurum_adi: str
) -> list[AdimOnerisi] | None:
    """3-5 adımlık plan; kurala uymayan çıktı bir kez düzeltme notuyla yeniden istenir.

    LLM hataları (hız sınırı 429, arıza 503) çağırana çıkar; kurala iki kez
    uymayan çıktıda None döner.
    """
    oneri = await _plan_cagir(plan_girdileri(ihtiyac, kart, kurum_adi))
    if plan_gecerli_mi(oneri):
        return oneri.adimlar
    logger.info("Plan önerisi kurala uymadı; düzeltme notuyla yeniden isteniyor")
    oneri = await _plan_cagir(plan_girdileri(ihtiyac, kart, kurum_adi, ek_not=DUZELTME_NOTU))
    if plan_gecerli_mi(oneri):
        return oneri.adimlar
    logger.warning("Plan önerisi iki denemede de kurala uymadı; plan boş bırakılıyor: %s", oneri)
    return None


# --- Firma–firma plan önerisi (docs/plans/firma-akisi.md § 9) ------------------------------
#
# Aynı kurallar ve aynı geçerlilik kontrolü; istem iki firma arasındaki iş birliğine
# göre (genç istemi değişmedi). Aday tarafı firma kartıyla anlatılır.

SISTEM_TALIMATI_FIRMA = SISTEM_TALIMATI.replace(
    "Bir kurum ile genç bir yetenek arasında\nyeni açılan bir pilot iş birliği",
    "İki firma arasında (ilanı açan firma ile\nortak firma) yeni açılan bir iş birliği",
).replace(
    "- Müsaitliği ve çalışma modelini hesaba kat: "
    "yarı zamanlı bir gence 2 haftada büyük iş verme.\n",
    "- İki firmanın ayrı ekipleri olduğunu hesaba kat: "
    "her adımda kimin ne teslim edeceği açık olsun.\n",
)

PLAN_SABLONU_FIRMA = ChatPromptTemplate.from_messages(
    [
        ("system", SISTEM_TALIMATI_FIRMA),
        (
            "human",
            """İlan (ilanı açan firma: {kurum_adi})
- Problem: {problem_tanimi}
- Başarı kriteri: {basari_kriteri}
- Kısıtlar: {kisitlar}
- İş birliği türü: {isbirligi_turu}

Ortak firma ({ortak_adi})
- Ne yapıyor: {ne_yapiyoruz}
- Yetkinlikler: {yetkinlikler}
- Önceki işler: {onceki_isler}
{ek_not}""",
        ),
    ]
)


def firma_plan_girdileri(
    ihtiyac: IhtiyacKarti, kart: FirmaKarti, kurum_adi: str, ek_not: str = ""
) -> dict:
    """İstem girdileri; iletişim bilgisi (e-posta) hiç girmez."""
    return {
        "kurum_adi": kurum_adi,
        "problem_tanimi": ihtiyac.problem_tanimi,
        "basari_kriteri": ihtiyac.basari_kriteri or "(yazılmamış)",
        "kisitlar": ihtiyac.kisitlar or "(yok)",
        "isbirligi_turu": ISBIRLIGI_TURU_ETIKETLERI.get(
            ihtiyac.isbirligi_turu or "", "(belirtilmemiş)"
        ),
        "ortak_adi": kart.kurum.ad,
        "ne_yapiyoruz": kart.ne_yapiyoruz,
        "yetkinlikler": ", ".join(kart.yetkinlikler or []) or "(belirtilmemiş)",
        "onceki_isler": kart.onceki_isler or "(yazılmamış)",
        "ek_not": ek_not,
    }


@lru_cache
def _firma_plan_zinciri() -> Runnable:
    return yedekli_zincir(
        "guclu",
        "takip_plan_firma",
        lambda m: PLAN_SABLONU_FIRMA | m.with_structured_output(PlanOnerisi),
    )


async def _firma_plan_cagir(girdiler: dict) -> PlanOnerisi:
    try:
        return await _firma_plan_zinciri().ainvoke(girdiler)
    except Exception as hata:
        raise llm_hatasini_cevir(hata) from hata


async def firma_plan_oner(
    ihtiyac: IhtiyacKarti, kart: FirmaKarti, kurum_adi: str
) -> list[AdimOnerisi] | None:
    """`plan_oner`'in firma–firma karşılığı: aynı kural, bir kez düzeltme, sonra None."""
    oneri = await _firma_plan_cagir(firma_plan_girdileri(ihtiyac, kart, kurum_adi))
    if plan_gecerli_mi(oneri):
        return oneri.adimlar
    oneri = await _firma_plan_cagir(
        firma_plan_girdileri(ihtiyac, kart, kurum_adi, ek_not=DUZELTME_NOTU)
    )
    if plan_gecerli_mi(oneri):
        return oneri.adimlar
    logger.warning("Firma planı iki denemede de kurala uymadı; plan boş bırakılıyor: %s", oneri)
    return None


# --- Durum özeti (docs/faz-c-takip.md § 5) — kesilebilir iş --------------------------------
#
# Döngü onsuz da tam çalışır: özet yalnızca `isbirligi.durum_ozeti`'ne yazılır,
# hiçbir kural ona bakmaz. LLM yoksa alan boş kalır, arayüz zaman çizelgesini
# yine eksiksiz gösterir.

OZET_EN_UZUN = 400

OZET_TALIMATI = """Sen Zemin360'ın Takip Ajanı'sın. Bir kurum ile bir genç arasındaki pilot iş
birliğinin durumunu EN FAZLA İKİ CÜMLEYLE özetliyorsun; iki taraf da bu özeti görecek.

Kurallar:
- Yalnızca verilen bilgileri kullan; sayı, tarih ya da olay UYDURMA.
- Nötr ve destekleyici dil: kimseyi suçlama, "ihmal etti" gibi yargı cümleleri kurma.
- Gecikmiş adım varsa adını söyle; karşı tarafın onayını bekleyen adım varsa kimin onayı
  beklendiğini söyle.
- İş birliği tamamlandıysa bunu ve kaç adımda tamamlandığını söyle.
- Madde işareti, başlık ya da emoji kullanma; düz, sade Türkçe."""
OZET_TALIMATI += KULLANICI_DILI_KURALLARI

OZET_SABLONU = ChatPromptTemplate.from_messages(
    [("system", OZET_TALIMATI), ("human", "{durum_bilgisi}")]
)


@dataclass(frozen=True)
class AdimDurumu:
    baslik: str
    hedef_tarih: dt.date | None
    genc_isaretledi: bool
    kurum_isaretledi: bool

    @property
    def tamamlandi(self) -> bool:
        return self.genc_isaretledi and self.kurum_isaretledi


def ozet_girdisi(
    *,
    durum: str,
    genc_adi: str,
    kurum_adi: str,
    adimlar: list[AdimDurumu],
    son_hareket: dt.date | None,
    bugun: dt.date,
    aday_etiketi: str = "genç",
) -> str:
    """Özet istemine giden, tamamen yapılandırılmış durum bilgisi (saf).

    `genc_adi` aday tarafının adı; firma–firma'da `aday_etiketi="ortak firma"`.
    """
    tamam = sum(a.tamamlandi for a in adimlar)
    satirlar = [
        f"Taraflar: {aday_etiketi} {genc_adi}, kurum {kurum_adi}.",
        f"İş birliği durumu: {DURUM_ADLARI.get(durum, durum)}.",
        f"Adımlar: {len(adimlar)} adımın {tamam} tanesi iki tarafça tamamlandı.",
    ]
    for adim in adimlar:
        if adim.tamamlandi:
            ne = "tamamlandı"
        elif adim.genc_isaretledi:
            ne = f"{genc_adi} tamamlandı dedi; {kurum_adi} tarafının onayı bekleniyor"
        elif adim.kurum_isaretledi:
            ne = f"{kurum_adi} tamamlandı dedi; {genc_adi} tarafının onayı bekleniyor"
        else:
            ne = "sürüyor"
        if not adim.tamamlandi and adim.hedef_tarih and adim.hedef_tarih < bugun:
            ne += f"; hedef tarihi {(bugun - adim.hedef_tarih).days} gün geçti (gecikmiş)"
        satirlar.append(f"- {adim.baslik}: {ne}.")
    if son_hareket is not None:
        satirlar.append(f"Son hareketten bu yana {(bugun - son_hareket).days} gün geçti.")
    return "\n".join(satirlar)


DURUM_ADLARI = {
    "plan_bekliyor": "plan henüz iki tarafça onaylanmadı",
    "aktif": "plan onaylandı, çalışma sürüyor",
    "tamamlandi": "tamamlandı",
}


@lru_cache
def _ozet_zinciri() -> Runnable:
    # Hızlı katman: kısa, sık; girdisi tamamen yapılandırılmış sayılar.
    return yedekli_zincir("hizli", "takip_ozet", lambda m: OZET_SABLONU | m | StrOutputParser())


async def durum_ozeti_yaz(durum_bilgisi: str) -> str | None:
    """En fazla iki cümle; boş ya da aşırı uzun çıktı None (özet boş kalır)."""
    try:
        metin = await _ozet_zinciri().ainvoke({"durum_bilgisi": durum_bilgisi})
    except Exception as hata:
        raise llm_hatasini_cevir(hata) from hata
    metin = " ".join(metin.split())
    if not metin or len(metin) > OZET_EN_UZUN:
        logger.warning("Durum özeti kullanılamadı (%d karakter)", len(metin))
        return None
    return metin
