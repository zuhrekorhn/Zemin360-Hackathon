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

from app.agents.takip_durumu import ISBIRLIGI_TAMAMLANDI
from app.core.calisma_modeli import sehir_eslesmeli_mi
from app.core.firma_dogrulama import DOGRULANDI
from app.core.firma_karti import ISBIRLIGI_TURU_ETIKETLERI
from app.core.firma_profili import FIRMA_TURU_ETIKETLERI
from app.core.is_kalemi import is_kalemi_metni
from app.core.kullanici_dili import KULLANICI_DILI_KURALLARI
from app.core.llm import llm_hatasini_cevir, yedekli_zincir
from app.core.metin import turkce_kucult
from app.core.sehir import sehir_kanonik
from app.models.eslesme import Eslesme
from app.models.firma_karti import FirmaKarti
from app.models.guven_skoru import GuvenSkoru
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.isbirligi import Isbirligi
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti

logger = logging.getLogger("zemin360.eslestirme")

# docs/matching-algorithm.md § 4-5
BENZERLIK_AGIRLIGI = 0.75
DOGRULAMA_AGIRLIGI = 0.25
TOP_N = 5
SKOR_ESIGI = 0.40
# Tamamlanmış pilot (Faz C, docs/faz-c-takip.md § 6): doğrulama bonusuna
# toplamsal eklenir, tavan 1.0. Pilotu olmayan kartın skoru değişmez; pilot
# skora en çok 0.25 × 0.5 = +0.125 ekler. Alakayı yaratmaz: benzerlik alt
# sınırı skordan önce uygulanmaya devam ediyor.
PILOT_BONUSU = 0.5
# Konu alakası için ayrı bir alt sınır (docs/matching-algorithm.md § 5).
# Doğrulama bonusu sıralamayı etkiler, alakayı YARATMAZ: iyi doğrulanmış bir
# kart tek başına +0.19 getirdiği için 0.34 benzerlikli alakasız bir aday
# toplam eşiği geçebiliyordu. Bu sınır skordan ÖNCE uygulanır.
BENZERLIK_ALT_SINIRI = 0.45
# Güven göstergesinin her başlığı 0-3 (agent-specs.md § 4); NULL başlık = "—".
GUVEN_BASLIK_TAVANI = 3

# ESLESME.durum değer kümesi (docs/data-schema.md § Tasarım Kararları)
DURUM_ONERILDI = "onerildi"
DURUM_ILGILENILIYOR = "ilgileniliyor"
DURUM_KABUL_EDILDI = "kabul_edildi"
DURUM_REDDEDILDI = "reddedildi"
# Gençten ilgi (docs/plans/genc-akisi.md § 4): genç ilgi gösterdi, kurumun yanıtı
# bekleniyor. Karar verilmiş kayıt sayılır: pipeline silmez, skorunu ve
# gerekçesini değiştirmez (plan § 0, karar 14).
DURUM_GENC_ILGILENDI = "genc_ilgilendi"
# Kurum "şimdilik değil" dedi ya da ihtiyaç kapandı. Gence "Kapandı" görünür.
DURUM_KAPANDI = "kapandi"

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
GEREKCE_TALIMATI += KULLANICI_DILI_KURALLARI

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
    # İki tarafın her adımı onayladığı, tamamlanmış iş birliği sayısı.
    tamamlanan_pilot: int = 0

    @property
    def skor(self) -> float:
        return skor_hesapla(self.benzerlik, self.dogrulama_bonus)

    @property
    def aday_kimligi(self) -> uuid.UUID:
        return self.yetenek_karti.id


# --- Firma adayı (docs/plans/firma-akisi.md § 0 kararlar 5, 13; § 4) -------------------
#
# Ortak ilanının adayları firma kartları. Aynı formül ve aynı iki sınır
# (benzerlik alt sınırı, skor eşiği, ilk N); bonus firmaya göre: GİRVAK'ın
# doğruladığı firma ve daha önce tamamlanmış bir iş birliği. Bonus alakayı
# yaratmaz: alt sınır skordan önce (§ 5). Firma metinleri için 0.45'in ayarı
# ölçülmedi (bilinen sınır).
FIRMA_DOGRULAMA_BONUSU = 0.5
FIRMA_ISBIRLIGI_BONUSU = 0.5


def firma_bonusu(dogrulandi: bool, tamamlanan_isbirligi: int) -> float:
    bonus = FIRMA_DOGRULAMA_BONUSU if dogrulandi else 0.0
    if tamamlanan_isbirligi >= 1:
        bonus += FIRMA_ISBIRLIGI_BONUSU
    return min(1.0, bonus)


@dataclass(frozen=True)
class FirmaAdayi:
    """Skorlanmış bir firma kartı; `siralayip_ele` için `Aday` ile aynı yüz."""

    firma_karti: FirmaKarti
    benzerlik: float
    dogrulama_bonus: float
    tamamlanan_isbirligi: int = 0

    @property
    def skor(self) -> float:
        return skor_hesapla(self.benzerlik, self.dogrulama_bonus)

    @property
    def aday_kimligi(self) -> uuid.UUID:
        return self.firma_karti.id


# --- Saf hesap (LLM ve DB olmadan test edilebilir) -------------------------


def gosterge_orani(bilesenler: Sequence[int | None]) -> float | None:
    """Bir çalışmanın göstergesini 0-1'e indirger; yalnızca dolu başlıklar sayılır.

    "—" (None) başlık ne cezadır ne bonus: değerlendirilmemiş başlık 0 sayılsaydı
    referans eklemek bile oranı düşürürdü (bulgu 17). Hiç dolu başlık yoksa None:
    çalışma ortalamaya girmez. Dört başlık doluysa sonuç eski `toplam / 12`'nin aynısı.
    """
    dolu = [b for b in bilesenler if b is not None]
    if not dolu:
        return None
    return sum(dolu) / (GUVEN_BASLIK_TAVANI * len(dolu))


def dogrulama_bonusu(
    guven_skorlari: Sequence[Sequence[int | None]], tamamlanan_pilot: int = 0
) -> float:
    """Kartın güven göstergelerini ve tamamlanmış pilotunu 0-1 aralığına indirger.

    Göstergesi olmayan kart 0 alır — **ceza değil, sadece bonus yok**
    (docs/matching-algorithm.md § 4). Kanıtsız kart elenmez.

    Tamamlanmış pilot (en az bir) `PILOT_BONUSU` ekler, toplam 1.0'ı geçmez.
    Pilotu olmayan kart için sonuç Faz C öncesiyle birebir aynı.
    """
    guven = 0.0
    oranlar = [o for g in guven_skorlari if (o := gosterge_orani(g)) is not None]
    if oranlar:
        guven = sum(oranlar) / len(oranlar)
    pilot = PILOT_BONUSU if tamamlanan_pilot >= 1 else 0.0
    return min(1.0, guven + pilot)


def skor_hesapla(benzerlik: float, dogrulama_bonus: float) -> float:
    return BENZERLIK_AGIRLIGI * benzerlik + DOGRULAMA_AGIRLIGI * dogrulama_bonus


def benzerlik_yeterli_mi(benzerlik: float) -> bool:
    """Aday konu olarak yeterince yakın mı? Skordan bağımsız bir ön koşul.

    Doğrulama bonusu bu kararın dışında tutuluyor — güven, alakalı adaylar
    arasında sıralamayı değiştirir; alakasız bir adayı alakalı yapmaz.
    """
    return benzerlik >= BENZERLIK_ALT_SINIRI


def siralayip_ele(adaylar: Sequence[Aday | FirmaAdayi]) -> list[Aday | FirmaAdayi]:
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

    yetenek_karti_id: uuid.UUID | None
    durum: str


def aday_kimligi(eslesme: EslesmeGorunumu) -> uuid.UUID:
    """Eşleşmenin aday kartı: yetenek kartı ya da firma kartı (tam biri dolu)."""
    return eslesme.yetenek_karti_id or getattr(eslesme, "firma_karti_id", None)


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
        if aday_kimligi(eslesme) not in kalanlar and eslesme.durum == DURUM_ONERILDI
    ]


def kilit_anahtari(ihtiyac_karti_id: uuid.UUID) -> int:
    """Aynı ihtiyaç kartı için pipeline'ı sıraya sokan advisory lock anahtarı.

    `pg_advisory_xact_lock` işaretli 64 bitlik bir tamsayı istiyor; UUID'nin
    ilk 8 baytı bu kadar ayırt edici. Farklı kartlar nadiren aynı anahtara
    düşse bile sonuç yalnızca kısa bir bekleme olur, yanlış veri değil.
    """
    return int.from_bytes(ihtiyac_karti_id.bytes[:8], "big", signed=True)


def eslesme_ekle_ifadesi(
    *,
    ihtiyac_karti_id: uuid.UUID,
    skor: float,
    yetenek_karti_id: uuid.UUID | None = None,
    firma_karti_id: uuid.UUID | None = None,
) -> Insert:
    """Yeni öneriyi ekler; aynı çift zaten varsa hiçbir şey yapmaz.

    Asıl koruma pipeline'daki kilit. Bu ifade ikinci güvenlik ağı: kilit
    bir gün atlanırsa bile UNIQUE kısıt ihlali 500'e dönüşmesin. Aday ya
    yetenek kartı ya firma kartı; çakışma sütunu ona göre.
    """
    if (yetenek_karti_id is None) == (firma_karti_id is None):
        raise ValueError("Tam bir aday kartı verilmeli (yetenek ya da firma)")
    aday_sutunu = "yetenek_karti_id" if yetenek_karti_id else "firma_karti_id"
    return (
        pg_insert(Eslesme)
        .values(
            id=uuid.uuid4(),
            ihtiyac_karti_id=ihtiyac_karti_id,
            yetenek_karti_id=yetenek_karti_id,
            firma_karti_id=firma_karti_id,
            skor=skor,
            durum=DURUM_ONERILDI,
        )
        .on_conflict_do_nothing(index_elements=["ihtiyac_karti_id", aday_sutunu])
    )


def aday_ekle_ifadesi(ihtiyac_karti_id: uuid.UUID, aday: Aday | FirmaAdayi) -> Insert:
    if isinstance(aday, FirmaAdayi):
        return eslesme_ekle_ifadesi(
            ihtiyac_karti_id=ihtiyac_karti_id, firma_karti_id=aday.aday_kimligi, skor=aday.skor
        )
    return eslesme_ekle_ifadesi(
        ihtiyac_karti_id=ihtiyac_karti_id, yetenek_karti_id=aday.aday_kimligi, skor=aday.skor
    )


# --- Doğrulama özeti (gerekçeye giden) -------------------------------------
# Eskiden gerekçeye ikili bir etiket gidiyordu: herhangi bir çıktının güven
# skoru kaydı varsa "kanıtları doğrulandı". Orijinallik 1/3 (link iddiayla
# ilgisiz) olan kart da "doğrulanmış" diye anlatılıyordu. Şimdi rubrik
# puanları, rubriğin kendi tanımlarıyla cümleye çevrilip gönderiliyor.

ORIJINALLIK_IFADELERI = {
    None: "kanıt değerlendirilmedi ya da otomatik okunamadı",
    0: "kanıt linki yok ya da açılmıyor",
    1: "kanıt linki açılıyor ama iddiayla ilişkisi zayıf",
    2: "kanıt iddiayla ilgili ama kişinin kendi işi olduğu belirsiz",
    3: "kanıt linki iddia edilen işin kendisine götürüyor",
}
OLCULEBILIRLIK_IFADELERI = {
    None: "sonuç henüz değerlendirilmedi",
    0: "sonuç belirtilmemiş",
    1: "sonuç yalnızca niteliksel anlatılmış",
    2: "sayı var ama neyin ölçüsü olduğu net değil",
    3: "sonuç sayıyla ve net biçimde ölçülmüş",
}
ROL_IFADELERI = {
    None: "rol henüz değerlendirilmedi",
    0: "kişinin bu işteki rolü yazmıyor",
    1: "kişinin rolü belirsiz",
    2: "rol yazılmış ama ekip içindeki payı belirsiz",
    3: "kişinin ne yaptığı açık",
}
UCUNCU_TARAF_IFADELERI = {
    None: "referans istenmedi ya da yanıt gelmedi",
    # 0 artık "olumsuz yanıt" demek; "yanıt yok" None (bulgu 19).
    0: "referans iddiayı doğrulamadı",
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
    return skor.kanit_orijinalligi == 3 or (skor.ucuncu_taraf_onayi or 0) >= 2


def kart_guclu_kanitli_mi(kart: YetenekKarti) -> bool:
    return any(
        cikti.guven_skoru is not None and guclu_kanitli_mi(cikti.guven_skoru)
        for cikti in kart.somut_ciktilar
    )


def pilot_ozeti(tamamlanan_pilot: int) -> str:
    """Gerekçe istemine giden tamamlanmış pilot satırı (Faz C)."""
    if tamamlanan_pilot < 1:
        return "Tamamlanmış pilot: yok."
    return (
        f"Tamamlanmış pilot: {tamamlanan_pilot} — platformda bir kurumla iş birliğini, "
        "iki tarafın her adımı onaylayarak tamamladı."
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
        # Hesabı olmayan profilin kartı önerilmez: kurum ilgilense bile kabul
        # edecek kimse yok, döngü çıkmaz sokakta biterdi. Faz B öncesi
        # profiller böyle (docs/faz-b-kimlik-ve-dongu.md § 8).
        .where(Kullanici.hesap_id.isnot(None))
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
        # Kural app/core/musaitlik.py › musaitlik_uyar_mi: tercih gencin
        # listesinde olmalı; listesi boş (belirtmemiş) genç elenmez.
        sorgu = sorgu.where(
            or_(
                func.cardinality(Kullanici.musaitlikler) == 0,
                Kullanici.musaitlikler.any(ihtiyac.musaitlik_tercihi),
            )
        )

    # Eşik ve Top-N skordan sonra uygulanıyor (doğrulama bonusu sıralamayı
    # değiştirebilir), ama yine de makul bir üst sınırla getiriyoruz.
    satirlar = (await oturum.execute(sorgu.order_by("uzaklik").limit(50))).all()
    pilotlar = await tamamlanan_pilot_sayilari(oturum, [kart.id for kart, _ in satirlar])

    return [
        Aday(
            yetenek_karti=kart,
            benzerlik=1.0 - float(uzaklik_degeri),
            tamamlanan_pilot=pilotlar.get(kart.id, 0),
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
                ],
                tamamlanan_pilot=pilotlar.get(kart.id, 0),
            ),
        )
        for kart, uzaklik_degeri in satirlar
    ]


async def tamamlanan_pilot_sayilari(
    oturum: AsyncSession, kart_idler: Sequence[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Kart başına tamamlanmış iş birliği sayısı (Faz C sinyali).

    Saklanmıyor, hesaplanıyor: tek doğruluk kaynağı `isbirligi.durum`; kartta
    ayrıca bir sayaç tutulsaydı iki kaynak ayrışabilirdi.
    """
    if not kart_idler:
        return {}
    satirlar = await oturum.execute(
        select(Eslesme.yetenek_karti_id, func.count(Isbirligi.id))
        .join(Isbirligi, Isbirligi.eslesme_id == Eslesme.id)
        .where(
            Eslesme.yetenek_karti_id.in_(list(kart_idler)),
            Isbirligi.durum == ISBIRLIGI_TAMAMLANDI,
        )
        .group_by(Eslesme.yetenek_karti_id)
    )
    return {kart_id: sayi for kart_id, sayi in satirlar.all()}


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


def gerekce_girdileri(
    ihtiyac: IhtiyacKarti, kart: YetenekKarti, ek_not: str = "", tamamlanan_pilot: int = 0
) -> dict:
    """Gerekçe şablonunun değişkenleri (canlı test de bunu kullanıyor)."""
    ciktilar = (
        "; ".join(
            f"{cikti.baslik}" + (f" — {metin}" if (metin := is_kalemi_metni(cikti)) else "")
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
        "dogrulama": f"{dogrulama_ozeti(kart)}\n{pilot_ozeti(tamamlanan_pilot)}",
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
    pilot = aday.tamamlanan_pilot
    metin = await _gerekce_cagir(gerekce_girdileri(ihtiyac, kart, tamamlanan_pilot=pilot))
    if kart_guclu_kanitli_mi(kart) or not dogrulama_iddiasi_var_mi(metin):
        return metin

    logger.info("Gerekçe güçlü kanıt yokken 'doğrulanmış' dedi; yeniden üretiliyor (%s)", kart.id)
    metin = await _gerekce_cagir(
        gerekce_girdileri(ihtiyac, kart, ek_not=DUZELTME_NOTU, tamamlanan_pilot=pilot)
    )
    if not dogrulama_iddiasi_var_mi(metin):
        return metin

    logger.warning(
        "Gerekçe iki denemede de güçlü kanıt yokken 'doğrulanmış' dedi; gerekçesiz "
        "bırakılıyor (%s): %s",
        kart.id,
        metin,
    )
    return None


async def firma_adaylarini_getir(oturum: AsyncSession, ihtiyac: IhtiyacKarti) -> list[FirmaAdayi]:
    """Ortak ilanının firma adayları (docs/plans/firma-akisi.md § 0 karar 5, § 4).

    Kesin şartlar SQL'de: kartı ve hesabı olan firma, ilanı açan firma değil,
    ilan tür seçtiyse o türlerden, ilan şehir şartı koyduysa o şehirde (şehir
    varsayılan olarak fark etmez). Sektör şart değil. Sonra benzerlik alt
    sınırı; eşik ve ilk N `siralayip_ele`'de.
    """
    if ihtiyac.embedding is None:
        return []
    uzaklik = FirmaKarti.embedding.cosine_distance(ihtiyac.embedding)
    sorgu = (
        select(FirmaKarti, uzaklik.label("uzaklik"))
        .join(Kurum, Kurum.id == FirmaKarti.kurum_id)
        .options(selectinload(FirmaKarti.kurum))
        .where(
            FirmaKarti.embedding.isnot(None),
            Kurum.hesap_id.isnot(None),
            FirmaKarti.kurum_id != ihtiyac.kurum_id,
            uzaklik <= 1.0 - BENZERLIK_ALT_SINIRI,
        )
    )
    if ihtiyac.aranan_firma_turleri:
        sorgu = sorgu.where(Kurum.tur.in_(list(ihtiyac.aranan_firma_turleri)))
    if ihtiyac.sehir_tercihi:
        sorgu = sorgu.where(Kurum.sehir == sehir_kanonik(ihtiyac.sehir_tercihi))

    satirlar = (await oturum.execute(sorgu.order_by("uzaklik").limit(50))).all()
    isbirlikleri = await firma_tamamlanan_isbirligi_sayilari(
        oturum, [kart.id for kart, _ in satirlar]
    )
    return [
        FirmaAdayi(
            firma_karti=kart,
            benzerlik=1.0 - float(uzaklik_degeri),
            tamamlanan_isbirligi=isbirlikleri.get(kart.id, 0),
            dogrulama_bonus=firma_bonusu(
                kart.kurum.dogrulama_durumu == DOGRULANDI, isbirlikleri.get(kart.id, 0)
            ),
        )
        for kart, uzaklik_degeri in satirlar
    ]


async def firma_tamamlanan_isbirligi_sayilari(
    oturum: AsyncSession, kart_idler: Sequence[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Firma kartı başına, aday olarak tamamladığı iş birliği sayısı (hesaplanır)."""
    if not kart_idler:
        return {}
    satirlar = await oturum.execute(
        select(Eslesme.firma_karti_id, func.count(Isbirligi.id))
        .join(Isbirligi, Isbirligi.eslesme_id == Eslesme.id)
        .where(
            Eslesme.firma_karti_id.in_(list(kart_idler)),
            Isbirligi.durum == ISBIRLIGI_TAMAMLANDI,
        )
        .group_by(Eslesme.firma_karti_id)
    )
    return {kart_id: sayi for kart_id, sayi in satirlar.all()}


# --- Firma adayı gerekçesi ---------------------------------------------------------------

FIRMA_GEREKCE_TALIMATI = """Bir firmanın iş birliği ortağı aradığı ilan ile aday
bir firmanın kartı arasındaki uyumu açıklıyorsun. Açıklamayı ilanı açan firma
okuyacak; aday firmadan üçüncü şahısla bahset.

Kurallar:
- 2-3 cümle. Daha uzun yazma.
- SADECE ilanda ve kartta yazan somut şeylere atıf yap: ürün ya da hizmet,
  yetkinlik, önceki iş, başarı kriteri. Kartta olmayan bir yetenek UYDURMA.
- "Güçlü bir ortak", "harika bir eşleşme" gibi genel geçer ifadeler KULLANMA.
- Zayıf tarafı gizleme: önceki iş yazılmamışsa bunu bir cümlede sakince belirt.
- "Doğrulanmış", "doğrulandı" ifadelerini YALNIZCA güven bilgisinde firma
  doğrulandı yazıyorsa kullan. Puan ya da oran verme.
- Türkçe, sade, abartısız. Karar ilanı açan firmanın; sen yalnızca neden bu
  firmanın önerildiğini anlat.
"""
FIRMA_GEREKCE_TALIMATI += KULLANICI_DILI_KURALLARI

FIRMA_GEREKCE_SABLONU = ChatPromptTemplate.from_messages(
    [
        ("system", FIRMA_GEREKCE_TALIMATI),
        (
            "human",
            "İLAN (iş birliği ortağı aranıyor)\n"
            "Problem: {problem}\n"
            "Başarı kriteri: {basari_kriteri}\n"
            "Kısıtlar: {kisitlar}\n"
            "İş birliği türü: {isbirligi_turu}\n\n"
            "ADAY FİRMA\n"
            "Tür ve sektör: {firma_turu}, {sektor}\n"
            "Ne yapıyor: {ne_yapiyoruz}\n"
            "Yetkinlikler: {yetkinlikler}\n"
            "Önceki işler: {onceki_isler}\n\n"
            "GÜVEN BİLGİSİ\n"
            "{guven}\n\n"
            "{ek_not}Bu eşleşmenin gerekçesini yaz.",
        ),
    ]
)


def firma_guven_ozeti(dogrulandi: bool, tamamlanan_isbirligi: int) -> str:
    satirlar = [
        "Firma doğrulandı: program ekibi firmayı doğruladı."
        if dogrulandi
        else "Firma henüz doğrulanmadı; firmayı doğrulanmış diye anlatma."
    ]
    if tamamlanan_isbirligi >= 1:
        satirlar.append(
            f"Tamamlanan iş birliği: {tamamlanan_isbirligi} (platformda, iki tarafın her adımı "
            "onaylamasıyla)."
        )
    else:
        satirlar.append("Tamamlanan iş birliği: yok.")
    return "\n".join(satirlar)


def firma_gerekce_girdileri(ihtiyac: IhtiyacKarti, aday: FirmaAdayi, ek_not: str = "") -> dict:
    kart = aday.firma_karti
    kurum = kart.kurum
    return {
        "problem": ihtiyac.problem_tanimi,
        "basari_kriteri": ihtiyac.basari_kriteri or "belirtilmedi",
        "kisitlar": ihtiyac.kisitlar or "belirtilmedi",
        "isbirligi_turu": ISBIRLIGI_TURU_ETIKETLERI.get(
            ihtiyac.isbirligi_turu or "", "belirtilmedi"
        ),
        "firma_turu": FIRMA_TURU_ETIKETLERI.get(kurum.tur or "", "türü belirtilmemiş"),
        "sektor": kurum.sektor or "sektörü belirtilmemiş",
        "ne_yapiyoruz": kart.ne_yapiyoruz,
        "yetkinlikler": ", ".join(kart.yetkinlikler) or "belirtilmedi",
        "onceki_isler": kart.onceki_isler or "belirtilmedi",
        "guven": firma_guven_ozeti(kurum.dogrulama_durumu == DOGRULANDI, aday.tamamlanan_isbirligi),
        "ek_not": ek_not,
    }


@lru_cache
def _firma_gerekce_zinciri() -> Runnable:
    return yedekli_zincir(
        "guclu", "eslestirme_firma_gerekce", lambda m: FIRMA_GEREKCE_SABLONU | m | StrOutputParser()
    )


FIRMA_DUZELTME_NOTU = (
    'DİKKAT: Önceki denemede firmayı "doğrulanmış" diye anlattın, oysa firma henüz '
    'doğrulanmadı. Bu kez "doğrulanmış" ya da "doğrulandı" deme.\n\n'
)


async def _firma_gerekce_cagir(girdiler: dict) -> str:
    try:
        metin = await _firma_gerekce_zinciri().ainvoke(girdiler)
    except Exception as hata:
        cevrilmis = llm_hatasini_cevir(hata)
        raise cevrilmis from hata
    return metin.strip()


async def firma_gerekce_uret(ihtiyac: IhtiyacKarti, aday: FirmaAdayi) -> str | None:
    """Genç gerekçesindeki korumanın aynısı: doğrulanmamış firma "doğrulanmış"
    diye anlatılırsa bir kez düzeltme notuyla yeniden; yine olursa gerekçesiz."""
    dogrulandi = aday.firma_karti.kurum.dogrulama_durumu == DOGRULANDI
    metin = await _firma_gerekce_cagir(firma_gerekce_girdileri(ihtiyac, aday))
    if dogrulandi or not dogrulama_iddiasi_var_mi(metin):
        return metin
    metin = await _firma_gerekce_cagir(
        firma_gerekce_girdileri(ihtiyac, aday, ek_not=FIRMA_DUZELTME_NOTU)
    )
    if not dogrulama_iddiasi_var_mi(metin):
        return metin
    logger.warning("Firma gerekçesi iki denemede de 'doğrulanmış' dedi; gerekçesiz bırakılıyor")
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
