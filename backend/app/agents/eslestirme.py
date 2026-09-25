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

import logging
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from sqlalchemy import Insert, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.calisma_modeli import sehir_eslesmeli_mi
from app.core.llm import llm_hatasini_cevir, yedekli_zincir
from app.core.metin import turkce_kucult
from app.core.sehir import sehir_kanonik
from app.models.eslesme import Eslesme
from app.models.guven_skoru import GuvenSkoru
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kullanici import Kullanici
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti

logger = logging.getLogger("zemin360.eslestirme")

# docs/matching-algorithm.md § 4-5
BENZERLIK_AGIRLIGI = 0.75
DOGRULAMA_AGIRLIGI = 0.25
TOP_N = 5
SKOR_ESIGI = 0.40
# Konu alakası için ayrı bir alt sınır (docs/matching-algorithm.md § 5).
# Doğrulama bonusu sıralamayı etkiler, alakayı YARATMAZ: iyi doğrulanmış bir
# kart tek başına +0.19 getirdiği için 0.34 benzerlikli alakasız bir aday
# toplam eşiği geçebiliyordu. Bu sınır skordan ÖNCE uygulanır.
BENZERLIK_ALT_SINIRI = 0.45
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
- Zayıf tarafı gizleme: kanıt zayıfsa ya da deneyim "potansiyel" ise bunu bir
  cümlede sakince belirt.
- "Doğrulanmış", "doğrulandı", "kanıtlanmış" gibi ifadeleri YALNIZCA doğrulama
  özetinin "Genel" satırı güçlü kanıt olduğunu söylüyorsa kullan. Aksi halde
  kanıtın ne durumda olduğunu özetteki ifadelerle anlat ("kanıt linki var ama
  iddiayla ilişkisi zayıf" gibi). Puanları rakamla verme.
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
            "Somut çıktılar: {ciktilar}\n\n"
            "DOĞRULAMA ÖZETİ (Doğrulama Ajanı'nın rubrik puanlarından)\n"
            "{dogrulama}\n\n"
            "{ek_not}Bu eşleşmenin gerekçesini yaz.",
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


def benzerlik_yeterli_mi(benzerlik: float) -> bool:
    """Aday konu olarak yeterince yakın mı? Skordan bağımsız bir ön koşul.

    Doğrulama bonusu bu kararın dışında tutuluyor — güven, alakalı adaylar
    arasında sıralamayı değiştirir; alakasız bir adayı alakalı yapmaz.
    """
    return benzerlik >= BENZERLIK_ALT_SINIRI


def siralayip_ele(adaylar: Sequence[Aday]) -> list[Aday]:
    """Alakasızları eler, skora göre sıralar, eşik altını atar, TOP_N'i döner.

    Alaka elemesi skor hesabından önce: bir aday konuyla ilgisizse ne kadar
    iyi doğrulanmış olduğu bu kararı değiştirmemeli.
    """
    uygunlar = [
        aday for aday in adaylar if benzerlik_yeterli_mi(aday.benzerlik) and aday.skor >= SKOR_ESIGI
    ]
    return sorted(uygunlar, key=lambda aday: aday.skor, reverse=True)[:TOP_N]


class EslesmeGorunumu(Protocol):
    """Temizlik kararı için bir eşleşmenin gereken yüzü."""

    yetenek_karti_id: uuid.UUID
    durum: str


def temizlenecekler(
    mevcutlar: Sequence[EslesmeGorunumu], secilenler: Sequence[uuid.UUID]
) -> list[EslesmeGorunumu]:
    """Yeniden hesapta artık uygun olmayan eşleşmelerden silinecekler.

    Yalnızca `onerildi` durumundakiler silinir: kurum bir kayda dokunduysa
    (ilgileniyor, kabul, red) o artık bir öneri değil, verilmiş bir karardır —
    kural değişti diye kurumun geçmişini silmek olmaz. Bunlar listede kalır,
    skorları tazelenmez.
    """
    kalanlar = set(secilenler)
    return [
        eslesme
        for eslesme in mevcutlar
        if eslesme.yetenek_karti_id not in kalanlar and eslesme.durum == DURUM_ONERILDI
    ]


def kilit_anahtari(ihtiyac_karti_id: uuid.UUID) -> int:
    """Aynı ihtiyaç kartı için pipeline'ı sıraya sokan advisory lock anahtarı.

    `pg_advisory_xact_lock` işaretli 64 bitlik bir tamsayı istiyor; UUID'nin
    ilk 8 baytı bu kadar ayırt edici. Farklı kartlar nadiren aynı anahtara
    düşse bile sonuç yalnızca kısa bir bekleme olur, yanlış veri değil.
    """
    return int.from_bytes(ihtiyac_karti_id.bytes[:8], "big", signed=True)


def eslesme_ekle_ifadesi(
    *, ihtiyac_karti_id: uuid.UUID, yetenek_karti_id: uuid.UUID, skor: float
) -> Insert:
    """Yeni öneriyi ekler; aynı çift zaten varsa hiçbir şey yapmaz.

    Asıl koruma pipeline'daki kilit. Bu ifade ikinci güvenlik ağı: kilit
    bir gün atlanırsa bile UNIQUE kısıt ihlali 500'e dönüşmesin.
    """
    return (
        pg_insert(Eslesme)
        .values(
            id=uuid.uuid4(),
            ihtiyac_karti_id=ihtiyac_karti_id,
            yetenek_karti_id=yetenek_karti_id,
            skor=skor,
            durum=DURUM_ONERILDI,
        )
        .on_conflict_do_nothing(index_elements=["ihtiyac_karti_id", "yetenek_karti_id"])
    )


# --- Doğrulama özeti (gerekçeye giden) -------------------------------------
# Eskiden gerekçeye ikili bir etiket gidiyordu: herhangi bir çıktının güven
# skoru kaydı varsa "kanıtları doğrulandı". Orijinallik 1/3 (link iddiayla
# ilgisiz) olan kart da "doğrulanmış" diye anlatılıyordu. Şimdi rubrik
# puanları, rubriğin kendi tanımlarıyla cümleye çevrilip gönderiliyor.

ORIJINALLIK_IFADELERI = {
    0: "kanıt linki yok ya da açılmıyor",
    1: "kanıt linki açılıyor ama iddiayla ilişkisi zayıf",
    2: "kanıt iddiayla ilgili ama kişinin kendi işi olduğu belirsiz",
    3: "kanıt linki iddia edilen işin kendisine götürüyor",
}
OLCULEBILIRLIK_IFADELERI = {
    0: "sonuç belirtilmemiş",
    1: "sonuç yalnızca niteliksel anlatılmış",
    2: "sayı var ama neyin ölçüsü olduğu net değil",
    3: "sonuç sayıyla ve net biçimde ölçülmüş",
}
ROL_IFADELERI = {
    0: "kişinin bu işteki rolü yazmıyor",
    1: "kişinin rolü belirsiz",
    2: "rol yazılmış ama ekip içindeki payı belirsiz",
    3: "kişinin ne yaptığı açık",
}
UCUNCU_TARAF_IFADELERI = {
    0: "üçüncü taraf onayı yok",
    1: "referansın yanıtı zayıf ya da çekimser",
    2: "bir referans olumlu yanıt verdi",
    3: "referans güçlü biçimde onayladı",
}


def guclu_kanitli_mi(skor: GuvenSkoru) -> bool:
    """Bu çıktı "doğrulanmış" diye anlatılabilir mi?

    İki yoldan: kanıt işin kendisine götürüyor (orijinallik 3/3) ya da bir
    referans olumlu yanıt verdi (üçüncü taraf 2 veya 3) — referansın olumlu
    yanıtı da doğrulamadır. Ölçülebilirlik ve rol netliği iddianın ne kadar
    açık yazıldığını ölçer, doğruluğunu değil; burada sayılmaz.
    """
    return skor.kanit_orijinalligi == 3 or skor.ucuncu_taraf_onayi >= 2


def kart_guclu_kanitli_mi(kart: YetenekKarti) -> bool:
    return any(
        cikti.guven_skoru is not None and guclu_kanitli_mi(cikti.guven_skoru)
        for cikti in kart.somut_ciktilar
    )


def dogrulama_ozeti(kart: YetenekKarti) -> str:
    """Gerekçe istemine giden dürüst doğrulama durumu.

    Çıktı başına dört bileşen, rubriğin tanımlarıyla; en altta modelin
    "doğrulanmış" deyip diyemeyeceğini söyleyen tek bir "Genel" satırı.
    """
    if not kart.somut_ciktilar:
        return "Genel: kartta somut çıktı yok (potansiyel); doğrulanacak bir iddia bulunmuyor."

    satirlar = []
    for cikti in kart.somut_ciktilar:
        skor = cikti.guven_skoru
        if skor is None:
            satirlar.append(f"- {cikti.baslik}: kanıt eklenmemiş, Doğrulama Ajanı'ndan geçmemiş.")
            continue
        satirlar.append(
            f"- {cikti.baslik}: "
            f"{ORIJINALLIK_IFADELERI[skor.kanit_orijinalligi]}; "
            f"{OLCULEBILIRLIK_IFADELERI[skor.sonuc_olculebilirligi]}; "
            f"{ROL_IFADELERI[skor.rol_netligi]}; "
            f"{UCUNCU_TARAF_IFADELERI[skor.ucuncu_taraf_onayi]}."
        )

    if kart_guclu_kanitli_mi(kart):
        genel = "Genel: en az bir çıktı güçlü kanıtla doğrulandı."
    elif any(c.guven_skoru is not None for c in kart.somut_ciktilar):
        genel = 'Genel: güçlü kanıt yok — kartı "doğrulanmış" diye anlatma.'
    else:
        genel = "Genel: hiçbir çıktı henüz doğrulanmadı."
    return "\n".join([*satirlar, genel])


# "Doğrulanmış / doğrulandı / doğrulanan / kanıtlanmış" — olumsuzları
# ("doğrulanmamış", "doğrulanmadı") yakalamaz: kökten hemen sonra "ma/me" geliyor.
_DOGRULAMA_IDDIASI = re.compile(r"(doğrulan|kanıtlan)(mış|dı|an)")


def dogrulama_iddiasi_var_mi(metin: str) -> bool:
    """Gerekçe kartı doğrulanmış diye mi anlatıyor?"""
    return bool(_DOGRULAMA_IDDIASI.search(turkce_kucult(metin)))


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
        # Alaka alt sınırı SQL'de de uygulanıyor: havuz embedding hesabından
        # sonra ama Python'a taşınmadan daralsın. Kural yine de saf
        # `siralayip_ele` tarafında duruyor (tek doğruluk kaynağı orası).
        .where(uzaklik <= 1.0 - BENZERLIK_ALT_SINIRI)
    )
    # Konum ve çalışma modeli ayrı filtreler:
    #  - İhtiyaç "uzaktan" ise şehrin hükmü yok, modeli kabul etmesi yeter.
    #  - "İş yerinde" / "hibrit" ise hem şehir eşleşmeli hem model kabul edilmeli.
    # Şehir karşılaştırması kanonik yazım üzerinden (app/core/sehir.py):
    # kayıtlar da aynı fonksiyondan geçtiği için düz eşitlik güvenli.
    if ihtiyac.sehir_tercihi and sehir_eslesmeli_mi(ihtiyac.calisma_modeli):
        sorgu = sorgu.where(Kullanici.sehir == sehir_kanonik(ihtiyac.sehir_tercihi))
    if ihtiyac.calisma_modeli:
        # Modelini hiç belirtmemiş kart elenmiyor: bilinmeyeni "hayır" saymak,
        # şehir yazımında düştüğümüz sessiz eleme hatasının aynısı olurdu.
        sorgu = sorgu.where(
            or_(
                func.cardinality(Kullanici.calisma_modelleri) == 0,
                Kullanici.calisma_modelleri.any(ihtiyac.calisma_modeli),
            )
        )
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
    # Güçlü katman: gerekçe kartlardaki somut noktalara atıf yapmalı, genel
    # geçer laf etmemeli — nüans burada önemli (app/core/llm.py).
    return yedekli_zincir(
        "guclu", "eslestirme_gerekce", lambda m: GEREKCE_SABLONU | m | StrOutputParser()
    )


DUZELTME_NOTU = (
    'DİKKAT: Önceki denemede kartı "doğrulanmış" diye anlattın, oysa doğrulama '
    'özeti güçlü kanıt olmadığını söylüyor. Bu kez "doğrulanmış", "doğrulandı" '
    'ya da "kanıtlanmış" deme; kanıtın durumunu özetteki ifadelerle anlat.\n\n'
)


def gerekce_girdileri(ihtiyac: IhtiyacKarti, kart: YetenekKarti, ek_not: str = "") -> dict:
    """Gerekçe şablonunun değişkenleri (canlı test de bunu kullanıyor)."""
    ciktilar = (
        "; ".join(
            f"{cikti.baslik}" + (f" — {cikti.aciklama}" if cikti.aciklama else "")
            for cikti in kart.somut_ciktilar
        )
        or "yok"
    )
    return {
        "problem": ihtiyac.problem_tanimi,
        "basari_kriteri": ihtiyac.basari_kriteri or "belirtilmedi",
        "kisitlar": ihtiyac.kisitlar or "belirtilmedi",
        "rol": kart.rol_alani,
        "deneyim": kart.deneyim_seviyesi,
        "sektorler": ", ".join(kart.sektor_ilgi_alani) or "belirtilmedi",
        "araclar": ", ".join(kart.araclar_teknolojiler) or "belirtilmedi",
        "ciktilar": ciktilar,
        "dogrulama": dogrulama_ozeti(kart),
        "ek_not": ek_not,
    }


async def _gerekce_cagir(girdiler: dict) -> str:
    try:
        metin = await _gerekce_zinciri().ainvoke(girdiler)
    except Exception as hata:
        cevrilmis = llm_hatasini_cevir(hata)
        raise cevrilmis from hata
    return metin.strip()


async def gerekce_uret(ihtiyac: IhtiyacKarti, aday: Aday) -> str | None:
    """Öneri başına 2-3 cümlelik gerekçe (docs/matching-algorithm.md § 6).

    Koruma: güçlü kanıt yokken model kartı "doğrulanmış" diye anlatırsa gerekçe
    düzeltme notuyla bir kez yeniden üretilir. Yine iddia ederse None döner —
    kuruma yanlış bir "doğrulandı" göstermektense gerekçesiz öneri daha iyi;
    skor geçerli kalır, sonraki hesapta gerekçe yeniden denenir.
    """
    kart = aday.yetenek_karti
    metin = await _gerekce_cagir(gerekce_girdileri(ihtiyac, kart))
    if kart_guclu_kanitli_mi(kart) or not dogrulama_iddiasi_var_mi(metin):
        return metin

    logger.info("Gerekçe güçlü kanıt yokken 'doğrulanmış' dedi; yeniden üretiliyor (%s)", kart.id)
    metin = await _gerekce_cagir(gerekce_girdileri(ihtiyac, kart, ek_not=DUZELTME_NOTU))
    if not dogrulama_iddiasi_var_mi(metin):
        return metin

    logger.warning(
        "Gerekçe iki denemede de güçlü kanıt yokken 'doğrulanmış' dedi; gerekçesiz "
        "bırakılıyor (%s): %s",
        kart.id,
        metin,
    )
    return None


async def ihtiyac_kartini_getir(oturum: AsyncSession, kurum_id: uuid.UUID) -> IhtiyacKarti | None:
    """Kurumun en son oluşturduğu ihtiyaç kartı.

    Sıralama `olusturma_tarihi`'ne göre: id bir UUID v4, zaman bilgisi
    taşımıyor (docs/data-schema.md § Tasarım Kararları).
    """
    return await oturum.scalar(
        select(IhtiyacKarti)
        .where(IhtiyacKarti.kurum_id == kurum_id)
        .order_by(IhtiyacKarti.olusturma_tarihi.desc())
        .limit(1)
    )
