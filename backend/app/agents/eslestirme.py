"""Eşleştirme Ajanı — ihtiyaç kartına en uygun yetenek kartlarını bulur.

**Bu bir sohbet ajanı değil.** Keşif ve Tanımlama çok turlu konuşma yürütür ve
`sohbet_motoru.py`'yi paylaşır; burada konuşma yok: tek seferlik bir hesap
(SQL filtre → pgvector benzerliği → skor → eşik) ve sonunda öneri başına bir
LLM çağrısı (gerekçe metni). Bu yüzden grafik/checkpointer da yok.

Dosya `app/agents/` altında duruyor çünkü belgelerdeki altı ajandan biri
(docs/agent-specs.md § 3) ve pipeline'ın tamamı — SQL'i, skoru, gerekçesi —
tek yerde okunabilsin istiyoruz; core/ ile agents/ arasına bölmek kimseye
yardım etmezdi.

Uygulama detayı: docs/matching-algorithm.md. MVP çekirdeği yazıldı, ESCO
taksonomi bileşeni (§ İsteğe Bağlı Geliştirme) bilinçli olarak dışarıda.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.llm import HizSinirHatasi, kota_hatasi_mi, model, yedekli_zincir
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kullanici import Kullanici
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti

# docs/matching-algorithm.md § 4-5
BENZERLIK_AGIRLIGI = 0.75
DOGRULAMA_AGIRLIGI = 0.25
TOP_N = 5
SKOR_ESIGI = 0.40
# Güven skorunun dört bileşeni de 0-3 → en yüksek toplam 12 (agent-specs.md § 4)
GUVEN_TAM_PUAN = 12

# ESLESME.durum değer kümesi (docs/data-schema.md § Tasarım Kararları)
DURUM_ONERILDI = "onerildi"
DURUM_ILGILENILIYOR = "ilgileniliyor"
DURUM_KABUL_EDILDI = "kabul_edildi"
DURUM_REDDEDILDI = "reddedildi"

GEREKCE_TALIMATI = """Sen Zemin360'ın Eşleştirme Ajanı'sın. Bir kurumun ihtiyaç kartı ile
bir gencin yetenek kartının neden eşleştiğini açıklıyorsun.

Kurallar:
- 2-3 cümle. Daha uzun yazma.
- SADECE kartlarda yazan somut şeylere atıf yap: rol, araç, sayı, başarı kriteri,
  çıktı başlığı. Kartta olmayan bir yetenek ya da deneyim UYDURMA.
- "İyi bir aday", "güçlü bir profil", "harika bir eşleşme" gibi genel geçer
  ifadeler KULLANMA. Bunlar hiçbir şey söylemiyor.
- Zayıf tarafı gizleme: kart doğrulanmamışsa ya da deneyim "potansiyel" ise
  bunu bir cümlede sakince belirt.
- Türkçe, sade, abartısız. Karar kurumun; sen sadece neden bu kartın önerildiğini
  anlat.
"""

GEREKCE_SABLONU = ChatPromptTemplate.from_messages(
    [
        ("system", GEREKCE_TALIMATI),
        (
            "human",
            "İHTİYAÇ KARTI\n"
            "Problem: {problem}\n"
            "Başarı kriteri: {basari_kriteri}\n"
            "Kısıtlar: {kisitlar}\n\n"
            "YETENEK KARTI\n"
            "Rol: {rol}\n"
            "Deneyim: {deneyim}\n"
            "Sektör ilgisi: {sektorler}\n"
            "Araçlar: {araclar}\n"
            "Somut çıktılar: {ciktilar}\n"
            "Doğrulama durumu: {dogrulama}\n\n"
            "Bu eşleşmenin gerekçesini yaz.",
        ),
    ]
)


@dataclass(frozen=True)
class Aday:
    """Skorlanmış bir yetenek kartı."""

    yetenek_karti: YetenekKarti
    benzerlik: float
    dogrulama_bonus: float

    @property
    def skor(self) -> float:
        return skor_hesapla(self.benzerlik, self.dogrulama_bonus)


# --- Saf hesap (LLM ve DB olmadan test edilebilir) -------------------------


def dogrulama_bonusu(guven_skorlari: Sequence[Sequence[int]]) -> float:
    """Kartın güven skorlarını 0-1 aralığına indirger.

    Skor kaydı olmayan kart 0 alır — **ceza değil, sadece bonus yok**
    (docs/matching-algorithm.md § 4). Kanıtsız kart elenmez.
    """
    if not guven_skorlari:
        return 0.0
    oranlar = [sum(bilesenler) / GUVEN_TAM_PUAN for bilesenler in guven_skorlari]
    return sum(oranlar) / len(oranlar)


def skor_hesapla(benzerlik: float, dogrulama_bonus: float) -> float:
    return BENZERLIK_AGIRLIGI * benzerlik + DOGRULAMA_AGIRLIGI * dogrulama_bonus


def siralayip_ele(adaylar: Sequence[Aday]) -> list[Aday]:
    """Skora göre sıralar, eşik altını atar, ilk TOP_N'i döner."""
    uygunlar = [aday for aday in adaylar if aday.skor >= SKOR_ESIGI]
    return sorted(uygunlar, key=lambda aday: aday.skor, reverse=True)[:TOP_N]


def kart_dogrulanmis_mi(kart: YetenekKarti) -> bool:
    return any(cikti.guven_skoru is not None for cikti in kart.somut_ciktilar)


# --- Veri katmanı ----------------------------------------------------------


async def adaylari_getir(oturum: AsyncSession, ihtiyac: IhtiyacKarti) -> list[Aday]:
    """Sert filtreler + pgvector benzerliği (docs/matching-algorithm.md § 3-4).

    Sert filtreler SQL'de, embedding hesabından ÖNCE çalışır: havuz önce
    daralır, benzerlik yalnızca kalan alt kümede hesaplanır.
    """
    if ihtiyac.embedding is None:
        return []

    uzaklik = YetenekKarti.embedding.cosine_distance(ihtiyac.embedding)
    sorgu = (
        select(YetenekKarti, uzaklik.label("uzaklik"))
        .join(Kullanici, Kullanici.id == YetenekKarti.kullanici_id)
        .options(selectinload(YetenekKarti.somut_ciktilar).selectinload(SomutCikti.guven_skoru))
        .where(YetenekKarti.embedding.isnot(None))
    )
    if ihtiyac.sehir_tercihi:
        sorgu = sorgu.where(Kullanici.sehir == ihtiyac.sehir_tercihi)
    if ihtiyac.musaitlik_tercihi:
        sorgu = sorgu.where(Kullanici.musaitlik == ihtiyac.musaitlik_tercihi)

    # Eşik ve Top-N skordan sonra uygulanıyor (doğrulama bonusu sıralamayı
    # değiştirebilir), ama yine de makul bir üst sınırla getiriyoruz.
    satirlar = (await oturum.execute(sorgu.order_by("uzaklik").limit(50))).all()

    return [
        Aday(
            yetenek_karti=kart,
            benzerlik=1.0 - float(uzaklik_degeri),
            dogrulama_bonus=dogrulama_bonusu(
                [
                    (
                        cikti.guven_skoru.kanit_orijinalligi,
                        cikti.guven_skoru.sonuc_olculebilirligi,
                        cikti.guven_skoru.rol_netligi,
                        cikti.guven_skoru.ucuncu_taraf_onayi,
                    )
                    for cikti in kart.somut_ciktilar
                    if cikti.guven_skoru is not None
                ]
            ),
        )
        for kart, uzaklik_degeri in satirlar
    ]


# --- Gerekçe (tek LLM çağrısı) ---------------------------------------------


@lru_cache
def _gerekce_zinciri() -> Runnable:
    return yedekli_zincir(lambda model_adi: GEREKCE_SABLONU | model(model_adi) | StrOutputParser())


async def gerekce_uret(ihtiyac: IhtiyacKarti, aday: Aday) -> str:
    """Öneri başına 2-3 cümlelik gerekçe (docs/matching-algorithm.md § 6)."""
    kart = aday.yetenek_karti
    ciktilar = (
        "; ".join(
            f"{cikti.baslik}" + (f" — {cikti.aciklama}" if cikti.aciklama else "")
            for cikti in kart.somut_ciktilar
        )
        or "yok"
    )
    dogrulama = (
        "kanıtları doğrulandı"
        if kart_dogrulanmis_mi(kart)
        else "henüz doğrulanmadı (Doğrulama Ajanı'ndan geçmemiş)"
    )

    try:
        metin = await _gerekce_zinciri().ainvoke(
            {
                "problem": ihtiyac.problem_tanimi,
                "basari_kriteri": ihtiyac.basari_kriteri or "belirtilmedi",
                "kisitlar": ihtiyac.kisitlar or "belirtilmedi",
                "rol": kart.rol_alani,
                "deneyim": kart.deneyim_seviyesi,
                "sektorler": ", ".join(kart.sektor_ilgi_alani) or "belirtilmedi",
                "araclar": ", ".join(kart.araclar_teknolojiler) or "belirtilmedi",
                "ciktilar": ciktilar,
                "dogrulama": dogrulama,
            }
        )
    except Exception as hata:
        if kota_hatasi_mi(hata):
            raise HizSinirHatasi(str(hata)) from hata
        raise

    return metin.strip()


async def ihtiyac_kartini_getir(oturum: AsyncSession, kurum_id: uuid.UUID) -> IhtiyacKarti | None:
    """Kurumun ihtiyaç kartı.

    Kurum başına birden fazla kart olabilir. Şemada oluşturulma tarihi alanı
    yok (docs/data-schema.md), yani "en yenisi" veriden türetilemiyor — bu
    yüzden id sırası kullanılıyor: deterministik ama kronolojik DEĞİL. Kurum
    birden fazla kart oluşturmaya başlayınca şemaya tarih alanı eklenmeli.
    """
    return await oturum.scalar(
        select(IhtiyacKarti)
        .where(IhtiyacKarti.kurum_id == kurum_id)
        .order_by(IhtiyacKarti.id.desc())
        .limit(1)
    )
