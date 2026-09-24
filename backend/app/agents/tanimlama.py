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
from typing import Any

from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, Field

from app.agents import sohbet_motoru as motor
from app.agents.sohbet_motoru import SohbetDurumu

ACILIS_SORUSU = (
    "Merhaba! Çözmeye çalıştığınız problemi anlatın — ne yaşıyorsunuz, "
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
- sehir_tercihi: yalnızca belirli bir şehir şartı varsa (yoksa boş).
- musaitlik_tercihi: tam zamanlı / yarı zamanlı / proje bazlı / staj gibi bir
  beklenti söylendiyse (yoksa boş).
"""

YEDEK_SORULAR = {
    "problem_tanimi": (
        "Bu kişi ya da ekip işe başladığında ilk hangi sorunu çözecek? "
        "Bugün o iş nasıl yürüyor ve nerede tıkanıyor?"
    ),
    "basari_kriteri": (
        "Bu iş bittiğinde neye bakıp “oldu” diyeceksiniz? Sayıyla ifade edebilir "
        "misiniz — bir oran, bir süre ya da bir adet?"
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
    sehir_tercihi: str | None = Field(
        default=None, description="Sadece belirli bir şehir şartı varsa"
    )
    musaitlik_tercihi: str | None = Field(
        default=None, description="tam_zamanli | yarim_zamanli | proje_bazli | staj"
    )
    takip_sorusu: str | None = Field(
        default=None,
        description=(
            "Eksik kalan alan için sorulacak tek bir sokratik soru. Belirsiz bir "
            "ifadeyi ölçülebilir hale getirmeyi hedefle."
        ),
    )


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
    return motor.cikarim_zinciri(IhtiyacCikarimi)


def bos_taslak() -> dict[str, Any]:
    return motor.bos_taslak(TANIMLAMA)


def grafik_derle(checkpointer: BaseCheckpointSaver):
    return motor.grafik_derle(TANIMLAMA, TanimlamaDurumu, checkpointer, _cikarim_zinciri)
