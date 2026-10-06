"""Takip Ajanı — süreç kişiselleştirme ve durum özeti (docs/faz-c-takip.md § 4-5).

Sohbet ajanı değil: tek seferlik hesap (kartlar → istem → tek LLM çağrısı),
Eşleştirme gerekçesiyle aynı desen. Ajan karar vermez.

Süreç adımlarını ajan UYDURMAZ (docs/plans/takip-surecleri.md): adımlar
eşleşmenin türüne göre sabit şablondan gelir (app/agents/takip_surecleri.py).
Ajan her adımın "ne olunca tamam sayılır" cümlesini ve hazırlık önerisini
ilana ve karta göre kişiselleştirir. Kural kodda: model hata verirse, zaman
aşımına uğrarsa ya da geçersiz çıktı dönerse o adımda şablonun kendi metni
kalır. `plan_hazirla` hiçbir zaman hata fırlatmaz ve boş plan dönmez.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from dataclasses import dataclass, replace
from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from app.agents.takip_surecleri import PlanAdimi, SurecSablonu, sablon_adimlari
from app.core import calisma_modeli, musaitlik
from app.core.firma_karti import ISBIRLIGI_TURU_ETIKETLERI
from app.core.istem_guvenligi import veri_kurali, veri_temizle
from app.core.kullanici_dili import KULLANICI_DILI_KURALLARI
from app.core.llm import llm_hatasini_cevir, yedekli_zincir
from app.models.firma_karti import FirmaKarti
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.yetenek_karti import YetenekKarti

logger = logging.getLogger("zemin360.takip")

EN_UZUN_TANIM = 300
EN_UZUN_ONERI = 600
# Arka plan işi takılı kalmasın; süre dolarsa şablon metni yazılır.
PLAN_ZAMAN_ASIMI_SN = 90
# Kullanıcıya gösterilmeyen kelime (docs/icerik-rehberi.md: "deneme işi").
YASAK_KELIMELER = ("pilot",)

ISTEM_ETIKETLERI = ("ilan", "aday")


class KisiselAdim(BaseModel):
    anahtar: str = Field(description="Verilen adımın anahtarı, değiştirmeden.")
    tamam_tanimi: str = Field(
        description="Ne olunca tamam sayılır: gözlemlenebilir tek cümle, bu ilana özgü."
    )
    oneri: str = Field(
        description="Hazırlık önerisi: 1-3 kısa cümle, bu ilana ve adaya özgü, somut."
    )


class KisiselPlan(BaseModel):
    adimlar: list[KisiselAdim] = Field(description="Verilen her adım için bir kayıt, aynı sırayla.")


SISTEM_TALIMATI = """Sen Zemin360'ın Takip Ajanı'sın. Bir eşleşmeden sonra açılan iş birliği
sürecinin SABİT adımları sana verilecek. Adım ekleme, çıkarma, birleştirme ya da sırasını
değiştirme; adımlar ve başlıkları değişmez. Görevin her adımı bu ilana ve bu adaya göre
kişiselleştirmek. Taraflar planı gözden geçirip düzenleyecek; sen karar vermiyorsun.

Her adım için, adımın anahtarını değiştirmeden:
- tamam_tanimi: "Bu adım ne olunca tamam sayılır?" sorusunun gözlemlenebilir, tek cümlelik
  yanıtı. Son adım ilandaki başarı kriterine doğrudan bağlanır.
- oneri: tarafların bu adıma nasıl hazırlanacağı, 1-3 kısa cümle. Görüşme adımında ilana
  uygun iki üç soru; deneme görevi ya da deneme işi adımında ilandaki problemin küçük, somut
  bir parçası; kapsam adımında yazılması gereken maddeler.

Kurallar:
- Kartlarda OLMAYAN bir sayı, araç, kişi ya da tarih UYDURMA. Başarı kriterindeki sayıları
  kullanabilirsin; başka sayı gerekiyorsa sayı yazma.
- Metinleri iki taraf da okuyacak: çoğul ve kişisiz yaz ("konuşun", "belirleyin").
- "Pilot" kelimesini kullanma; "deneme işi" de.
- Teknik rol ve araç adlarını Türkçeleştirme (backend, API gibi yaygın adları koru).
- Düz, sade Türkçe."""
SISTEM_TALIMATI += veri_kurali(*ISTEM_ETIKETLERI) + KULLANICI_DILI_KURALLARI

PLAN_SABLONU = ChatPromptTemplate.from_messages(
    [
        ("system", SISTEM_TALIMATI),
        (
            "human",
            """Süreç: {surec_adi}
Adımlar (anahtar: başlık):
{adimlar}

İLAN (ilanı açan firma: {kurum_adi})
<ilan>
{ilan}
</ilan>

{aday_basligi}
<aday>
{aday}
</aday>""",
        ),
    ]
)


def _ilan_metni(ihtiyac: IhtiyacKarti, aday_firma: bool) -> str:
    satirlar = [
        f"Problem: {ihtiyac.problem_tanimi}",
        f"Başarı kriteri: {ihtiyac.basari_kriteri or '(yazılmamış)'}",
        f"Kısıtlar: {ihtiyac.kisitlar or '(yok)'}",
    ]
    if aday_firma:
        tur = ISBIRLIGI_TURU_ETIKETLERI.get(ihtiyac.isbirligi_turu or "", "(belirtilmemiş)")
        satirlar.append(f"İş birliği türü: {tur}")
    else:
        satirlar += [
            "Müsaitlik: "
            + musaitlik.ETIKETLER.get(ihtiyac.musaitlik_tercihi or "", "(belirtilmemiş)"),
            "Çalışma modeli: "
            + calisma_modeli.ETIKETLER.get(ihtiyac.calisma_modeli or "", "(belirtilmemiş)"),
        ]
    return "\n".join(satirlar)


def _genc_metni(kart: YetenekKarti) -> str:
    return "\n".join(
        [
            f"Rol: {kart.rol_alani} ({kart.deneyim_seviyesi})",
            "Araçlar: " + (", ".join(kart.araclar_teknolojiler or []) or "(belirtilmemiş)"),
            "Daha önce yaptığı işler: "
            + ("; ".join(c.baslik for c in kart.somut_ciktilar) or "(yok)"),
        ]
    )


def _firma_metni(kart: FirmaKarti) -> str:
    return "\n".join(
        [
            f"Ne yapıyor: {kart.ne_yapiyoruz}",
            "Yetkinlikler: " + (", ".join(kart.yetkinlikler or []) or "(belirtilmemiş)"),
            f"Önceki işler: {kart.onceki_isler or '(yazılmamış)'}",
        ]
    )


def plan_girdileri(
    sablon: SurecSablonu,
    ihtiyac: IhtiyacKarti,
    kurum_adi: str,
    *,
    yetenek_karti: YetenekKarti | None = None,
    firma_karti: FirmaKarti | None = None,
) -> dict:
    """İstem girdileri; aday ya genç ya ortak firma. İletişim bilgisi (e-posta) hiç girmez."""
    aday_firma = firma_karti is not None
    girdiler = {
        "surec_adi": sablon.ad,
        "adimlar": "\n".join(f"- {a.anahtar}: {a.baslik}" for a in sablon.adimlar),
        "kurum_adi": kurum_adi,
        "ilan": _ilan_metni(ihtiyac, aday_firma),
        "aday_basligi": (
            f"ORTAK FİRMA ({firma_karti.kurum.ad})" if aday_firma else "ADAY (genç yetenek)"
        ),
        "aday": _firma_metni(firma_karti) if aday_firma else _genc_metni(yetenek_karti),
    }
    return veri_temizle(girdiler, ISTEM_ETIKETLERI)


def _kullanilabilir(metin: str | None, en_uzun: int) -> str | None:
    """Modelin metni kurala uyuyorsa kırpılmış hali, uymuyorsa None (şablon metni kalır)."""
    metin = " ".join((metin or "").split())
    if not metin or len(metin) > en_uzun:
        return None
    if any(kelime in metin.casefold() for kelime in YASAK_KELIMELER):
        return None
    return metin


def kisisellestir(adimlar: list[PlanAdimi], oneri: KisiselPlan | None) -> list[PlanAdimi]:
    """Şablon adımlarına modelin metnini işler (saf). Eşleşmeyen, boş, uzun ya da
    yasak kelimeli metin şablondakiyle kalır; adım sayısı ve sırası değişmez."""
    if oneri is None:
        return list(adimlar)
    kisisel = {a.anahtar: a for a in oneri.adimlar}
    sonuc = []
    for adim in adimlar:
        gelen = kisisel.get(adim.anahtar)
        if gelen is None:
            sonuc.append(adim)
            continue
        sonuc.append(
            replace(
                adim,
                tamam_tanimi=_kullanilabilir(gelen.tamam_tanimi, EN_UZUN_TANIM)
                or adim.tamam_tanimi,
                oneri=_kullanilabilir(gelen.oneri, EN_UZUN_ONERI) or adim.oneri,
            )
        )
    return sonuc


@lru_cache
def _plan_zinciri() -> Runnable:
    # Güçlü katman: tek seferlik, nüans önemli (ilana özgü, uydurma yok).
    return yedekli_zincir(
        "guclu", "takip_plan", lambda m: PLAN_SABLONU | m.with_structured_output(KisiselPlan)
    )


async def plan_hazirla(sablon: SurecSablonu, baslangic: dt.date, girdiler: dict) -> list[PlanAdimi]:
    """Süreç planı: şablon adımları, model başarılıysa kişiselleştirilmiş.

    Hiçbir zaman hata fırlatmaz ve boş dönmez: hız sınırı, arıza, zaman aşımı
    ya da kurala uymayan çıktıda şablonun kendi metni kullanılır.
    """
    adimlar = sablon_adimlari(sablon, baslangic)
    try:
        oneri = await asyncio.wait_for(
            _plan_zinciri().ainvoke(girdiler), timeout=PLAN_ZAMAN_ASIMI_SN
        )
    except Exception:
        logger.warning("Plan kişiselleştirilemedi; şablon metni kullanılıyor", exc_info=True)
        return adimlar
    if not isinstance(oneri, KisiselPlan):
        logger.warning("Plan kişiselleştirmesi beklenmeyen tipte döndü: %r", type(oneri))
        return adimlar
    return kisisellestir(adimlar, oneri)


# --- Durum özeti (docs/faz-c-takip.md § 5) — kesilebilir iş --------------------------------
#
# Döngü onsuz da tam çalışır: özet yalnızca `isbirligi.durum_ozeti`'ne yazılır,
# hiçbir kural ona bakmaz. LLM yoksa alan boş kalır, arayüz zaman çizelgesini
# yine eksiksiz gösterir.

OZET_EN_UZUN = 400

OZET_TALIMATI = """Sen Zemin360'ın Takip Ajanı'sın. Eşleşmeden sonra açılan bir iş birliği
sürecinin durumunu EN FAZLA İKİ CÜMLEYLE özetliyorsun; iki taraf da bu özeti görecek.

Kurallar:
- Yalnızca verilen bilgileri kullan; sayı, tarih ya da olay UYDURMA.
- Nötr ve destekleyici dil: kimseyi suçlama, "ihmal etti" gibi yargı cümleleri kurma.
- Gecikmiş adım varsa adını söyle; karşı tarafın onayını bekleyen adım varsa kimin onayı
  beklendiğini söyle.
- İş birliği tamamlandıysa bunu ve kaç adımda tamamlandığını söyle.
- "Pilot" kelimesini kullanma; "deneme işi" de.
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
