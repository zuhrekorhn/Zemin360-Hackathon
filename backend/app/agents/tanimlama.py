"""Tanımlama Ajanı — kurumun dağınık ihtiyacını ihtiyaç kartı taslağına çevirir.

docs/agent-specs.md § 2:
  - Keşif ile AYNI sohbet motorunu paylaşır (app/agents/sohbet_motoru.py),
    sadece soru seti farklıdır.
  - Sokratik sorularla belirsiz ifadeyi ("dijitalleşmek istiyoruz") ölçülebilir
    hale getirir ("tier-1 biletlerin %50'sini insan olmadan çöz").
  - Kurumun stratejik kararını vermez, sadece ifadesini netleştirir.

Keşif'teki "hiç projem yok" fallback zincirinin karşılığı burada YOK —
spec'te böyle bir dal tanımlanmamış. Tek dal: eksik alan takibi (2 tur).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, Field

from app.agents import sohbet_motoru as motor
from app.agents.sohbet_motoru import SohbetDurumu
from app.core.kullanici_dili import KULLANICI_DILI_KURALLARI
from app.core.musaitlik import Musaitlik

ACILIS_SORUSU = (
    "Merhaba! Çözmeye çalıştığınız problemi anlatın: ne yaşıyorsunuz, "
    "kim etkileniyor? Henüz net değilse de olur, birlikte netleştiririz."
)

ZORUNLU_ALANLAR = ("problem_tanimi", "basari_kriteri")

SISTEM_TALIMATI = """Sen Zemin360'ın Tanımlama Ajanı'sın. Bir kurum temsilcisiyle
konuşuyorsun ve onun dağınık ihtiyacını yapılandırılmış bir ihtiyaç kartına çeviriyorsun.

Nasıl konuşursun:
- Sokratik ol: belirsiz ifadeyi ölçülebilir hale getir. "Dijitalleşmek istiyoruz"
  cümlesini "tier-1 destek biletlerinin %50'si insan müdahalesi olmadan çözülsün"
  gibi sayılabilir bir kritere indirgemeye çalış.
- Kurumun stratejik kararını SEN VERME. Ne yapmaları gerektiğini söyleme; sadece
  söylediklerini netleştir.
- Sektöre özel bir şablon dayatma; yapı sektör-nötr, sadece örneklerini uyarlarsın.
- Söylenmeyen bir şeyi UYDURMA. Emin olmadığın alanı boş bırak.
- Türkçe, sade ve profesyonel konuş; tek seferde tek soru sor.

ROL TARİFİ PROBLEM DEĞİLDİR:
Kurum sık sık bir kişi ya da pozisyon tarif ederek başlar: "3 yıl deneyimli
full stack developer arıyoruz", "bir sosyal medya uzmanı lazım". Bunu OLDUĞU
GİBİ problem_tanimi'na YAZMA — bu bir iş ilanı, problem değil. Bu durumda:
- problem_tanimi'nı boş bırak ve şunu sor: "Bu kişi işe başladığında ilk
  hangi sorunu çözecek? Bugün o iş nasıl yürüyor, nerede tıkanıyor?"
- Kurum problemi anlattığında problem_tanimi'na ONU yaz; aranan rol bir çözüm
  tercihidir, isterse kisitlar alanına geçebilir ("full stack bir kişi
  düşünüyorlar" gibi).
- Ekip/teknoloji tercihi de aynı şekilde: çözüm önerisi, problem değil.

Alanlar:
- problem_tanimi: kurumun yaşadığı somut problem, kendi ifadesiyle ama toparlanmış.
  Bir rol/pozisyon tarifi buraya yazılmaz (yukarıdaki kurala bak).
- basari_kriteri: "bu iş başarılı oldu" demelerini sağlayacak ÖLÇÜLEBİLİR kriter.
  Sayı, oran veya süre içermeli. Kurum ölçülebilir bir şey söylemediyse boş bırak
  ve takip sorusunda bunu sor.
- kisitlar: bütçe, süre, mevzuat, ekip gibi serbest metin kısıtlar.
- sehir_tercihi: işin yapılacağı şehir, yalnızca bir şehir şartı varsa (yoksa boş).
- calisma_modeli: işin nerede yapılacağı — "is_yerinde", "hibrit" veya
  "uzaktan" değerlerinden biri. Kurum "ofiste olsun", "haftada iki gün gelsin",
  "uzaktan da olur" gibi bir şey söylediyse doldur; söylemediyse boş bırak.
  Bu, müsaitlikten (tam/yarı zamanlı) FARKLI bir şey — karıştırma.
- musaitlik_tercihi: tam zamanlı / yarı zamanlı / proje bazlı / staj gibi bir
  beklenti söylendiyse (yoksa boş).

takip_sorusu ve takip_konusu: problem_tanimi ya da basari_kriteri eksikse
takip sorusunda ÖNCE bunlardan birini sor ve takip_konusu'na o alanın adını
yaz. Sorunun konusu eksik bir zorunlu alan değilse sistem senin soruna yer vermez.
"""
SISTEM_TALIMATI += KULLANICI_DILI_KURALLARI

YEDEK_SORULAR = {
    "problem_tanimi": (
        "Bu kişi ya da ekip işe başladığında ilk hangi sorunu çözecek? "
        "Bugün o iş nasıl yürüyor ve nerede tıkanıyor?"
    ),
    "basari_kriteri": (
        "Bu iş bittiğinde neye bakıp “oldu” diyeceksiniz? Sayıyla ifade edebilir "
        "misiniz? Örneğin bir oran, bir süre ya da bir adet."
    ),
}


class IhtiyacCikarimi(BaseModel):
    """LLM'in her turda döndürdüğü yapılandırılmış çıkarım.

    Boş gelen alan mevcut taslağın üzerine YAZMAZ (motor birleştirmesi).
    """

    problem_tanimi: str | None = None
    basari_kriteri: str | None = Field(
        default=None,
        description="Ölçülebilir olmalı (sayı/oran/süre). Değilse boş bırak.",
    )
    kisitlar: str | None = Field(
        default=None, description="Bütçe, süre, mevzuat, ekip gibi kısıtlar"
    )
    calisma_modeli: Literal["is_yerinde", "hibrit", "uzaktan"] | None = Field(
        default=None,
        description="İşin nerede yapılacağı; müsaitlikle (çalışma tipi) karıştırma",
    )
    sehir_tercihi: str | None = Field(
        default=None, description="Sadece belirli bir şehir şartı varsa"
    )
    # Literal: serbest metin ("tam zamanlı") eşleştirmenin düz eşitlik
    # filtresinde gencin koduyla eşleşmiyor, tüm adayları sessizce eliyordu.
    musaitlik_tercihi: Musaitlik | None = Field(
        default=None, description="Çalışma tipi; söylenmediyse boş bırak"
    )
    takip_sorusu: str | None = Field(
        default=None,
        description=(
            "Eksik kalan alan için sorulacak tek bir sokratik soru. Belirsiz bir "
            "ifadeyi ölçülebilir hale getirmeyi hedefle."
        ),
    )
    # Sistem, soruyu yalnızca konusu eksik bir zorunlu alansa kullanıyor
    # (sohbet_motoru.zorunlu_alan_sorusu).
    takip_konusu: (
        Literal[
            "problem_tanimi",
            "basari_kriteri",
            "kisitlar",
            "sehir_tercihi",
            "calisma_modeli",
            "musaitlik_tercihi",
            "diger",
        ]
        | None
    ) = Field(default=None, description="takip_sorusu hangi alanı soruyor")


class TanimlamaDurumu(SohbetDurumu, total=False):
    """Ortak durumun aynısı — Tanımlama'nın ek dalı yok."""


TANIMLAMA = motor.AjanTanimi(
    ad="tanimlama",
    acilis_sorusu=ACILIS_SORUSU,
    sistem_talimati=SISTEM_TALIMATI,
    cikarim_semasi=IhtiyacCikarimi,
    skaler_alanlar=(
        "problem_tanimi",
        "basari_kriteri",
        "kisitlar",
        "sehir_tercihi",
        "calisma_modeli",
        "musaitlik_tercihi",
    ),
    zorunlu_alanlar=ZORUNLU_ALANLAR,
    # Tanımlama iki turda kapanmaya devam ediyor: kurumun problemi iki soruda
    # netleşmiyorsa daha fazla sormak yerine taslağı göstermek daha iyi,
    # kurum kartı elle düzeltebiliyor. (Keşif'te tavan daha yüksek.)
    maks_zorunlu_turu=motor.MAKS_TAKIP_TURU,
    yedek_sorular=YEDEK_SORULAR,
    tamamla=lambda taslak: motor.zorunlu_alanlari_doldur(
        taslak, ZORUNLU_ALANLAR, metin_alanlari=ZORUNLU_ALANLAR
    ),
)


@lru_cache
def _cikarim_zinciri() -> Runnable:
    return motor.cikarim_zinciri(IhtiyacCikarimi, "tanimlama_cikarim")


def bos_taslak() -> dict[str, Any]:
    return motor.bos_taslak(TANIMLAMA)


def grafik_derle(checkpointer: BaseCheckpointSaver):
    return motor.grafik_derle(TANIMLAMA, TanimlamaDurumu, checkpointer, _cikarim_zinciri)


# --- Ortak ilanı (docs/plans/firma-akisi.md § 0 karar 4, § 5) ---------------------------
#
# Aynı motor, aynı ihtiyaç kartı; ikinci bir soru seti. Firma "iş birliği ortağı"
# kapısından gelince bu tanım kullanılır: çalışma modeli ve müsaitlik sorulmaz
# (genç ilanına özel), yerine iş birliği türü ve aranan firma türleri gelir.
# Firmanın kayıt bilgileri bağlam olarak gider, sorulmaz.

ACILIS_SORUSU_ORTAK = (
    "Merhaba! Bir iş birliği ortağıyla çözmek istediğiniz problemi anlatın: "
    "bugün ne yaşıyorsunuz ve ortaktan ne bekliyorsunuz?"
)

SISTEM_TALIMATI_ORTAK = """Zemin360'ta bir firmanın temsilcisiyle konuşuyorsun. Firma
başka bir firmayla (girişim, KOBİ ya da kurumsal) iş birliği yapmak istiyor.
Amacın, onun ihtiyacını yapılandırılmış bir ilana çevirmek; bu ilana uyan
firmalar önerilecek.

Nasıl konuşursun:
- Sokratik ol: belirsiz ifadeyi ölçülebilir hale getir ("stok maliyetini düşürmek"
  yerine "bozulan ürün oranını 6 ayda %20 azaltmak").
- Firmanın stratejik kararını SEN VERME; yalnızca söylediğini netleştir.
- Söylenmeyen bir şeyi UYDURMA. Emin olmadığın alanı boş bırak.
- Türkçe, sade ve profesyonel; firmaya "siz" diye hitap et. Tek seferde tek soru.
- Firmanın kayıt bilgilerini (adı, türü, sektörü, şehri) SORMA; bağlam olarak verilecek.

Alanlar:
- problem_tanimi: iş birliğiyle çözülecek somut problem, toparlanmış. "Bir yapay
  zekâ girişimi arıyoruz" gibi bir ortak tarifi problem değildir: bu durumda
  problem_tanimi'nı boş bırak ve ortağın hangi sorunu çözeceğini sor.
- basari_kriteri: iş birliği başarılı oldu demelerini sağlayacak ÖLÇÜLEBİLİR kriter
  (sayı, oran ya da süre). Söylenmediyse boş bırak.
- kisitlar: bütçe, süre, mevzuat, veri paylaşımı gibi kısıtlar.
- isbirligi_turu: pilot, tedarik, ortak_urun, yatirim ya da diger; söylenmediyse boş.
- aranan_firma_turleri: girisim, kobi, kurumsal değerlerinden söylenenler; söylenmediyse boş.
- sehir_tercihi: yalnızca ortağın belirli bir şehirde olması şartsa (yoksa boş).

takip_sorusu ve takip_konusu: problem_tanimi ya da basari_kriteri eksikse takip
sorusunda ÖNCE bunlardan birini sor ve takip_konusu'na o alanın adını yaz.
"""
SISTEM_TALIMATI_ORTAK += KULLANICI_DILI_KURALLARI

YEDEK_SORULAR_ORTAK = {
    "problem_tanimi": (
        "Ortak firma işe başladığında hangi sorunu çözecek? Bugün o iş nasıl "
        "yürüyor ve nerede tıkanıyor?"
    ),
    "basari_kriteri": (
        "Bu iş birliği bittiğinde neye bakıp “oldu” diyeceksiniz? Sayıyla ifade "
        "edebilir misiniz: bir oran, bir süre ya da bir adet?"
    ),
}


class OrtakIlanCikarimi(BaseModel):
    """Ortak ilanı için yapılandırılmış çıkarım; boş alan taslağı ezmez."""

    problem_tanimi: str | None = None
    basari_kriteri: str | None = Field(
        default=None, description="Ölçülebilir olmalı (sayı/oran/süre). Değilse boş bırak."
    )
    kisitlar: str | None = None
    isbirligi_turu: Literal["pilot", "tedarik", "ortak_urun", "yatirim", "diger"] | None = None
    aranan_firma_turleri: list[Literal["girisim", "kobi", "kurumsal"]] = Field(
        default_factory=list, description="Söylenen ortak türleri; söylenmediyse boş"
    )
    sehir_tercihi: str | None = Field(
        default=None, description="Sadece ortağın belirli bir şehirde olması şartsa"
    )
    takip_sorusu: str | None = None
    takip_konusu: (
        Literal[
            "problem_tanimi",
            "basari_kriteri",
            "kisitlar",
            "isbirligi_turu",
            "aranan_firma_turleri",
            "sehir_tercihi",
            "diger",
        ]
        | None
    ) = Field(default=None, description="takip_sorusu hangi alanı soruyor")


TANIMLAMA_ORTAK = motor.AjanTanimi(
    ad="tanimlama_ortak",
    acilis_sorusu=ACILIS_SORUSU_ORTAK,
    sistem_talimati=SISTEM_TALIMATI_ORTAK,
    cikarim_semasi=OrtakIlanCikarimi,
    skaler_alanlar=(
        "problem_tanimi",
        "basari_kriteri",
        "kisitlar",
        "isbirligi_turu",
        "sehir_tercihi",
    ),
    liste_alanlari=("aranan_firma_turleri",),
    zorunlu_alanlar=ZORUNLU_ALANLAR,
    maks_zorunlu_turu=motor.MAKS_TAKIP_TURU,
    yedek_sorular=YEDEK_SORULAR_ORTAK,
    tamamla=lambda taslak: motor.zorunlu_alanlari_doldur(
        taslak, ZORUNLU_ALANLAR, metin_alanlari=ZORUNLU_ALANLAR
    ),
)


@lru_cache
def _ortak_cikarim_zinciri() -> Runnable:
    return motor.cikarim_zinciri(OrtakIlanCikarimi, "tanimlama_ortak_cikarim")


def bos_ortak_taslak() -> dict[str, Any]:
    return motor.bos_taslak(TANIMLAMA_ORTAK)


def ortak_grafik_derle(checkpointer: BaseCheckpointSaver):
    return motor.grafik_derle(
        TANIMLAMA_ORTAK, TanimlamaDurumu, checkpointer, _ortak_cikarim_zinciri
    )
