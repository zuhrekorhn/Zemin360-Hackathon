"""Canlılık Ajanı — hatırlatma metinleri (docs/canlilik.md § 5).

Her türün sabit bir şablon metni var: LLM kişiselleştirmesi (kesilebilir)
yanıt vermezse ya da kesilirse hatırlatma bu metinle aynen gider, asla
kaybolmaz. Metinde ad olabilir, e-posta olmaz; dil nötr ve destekleyici.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.agents.canlilik_kurallari import (
    ADIM_GECIKTI,
    GENC_ILGISI_YANITSIZ,
    ILGI_YANITSIZ_1,
    ILGI_YANITSIZ_2,
    ISBIRLIGI_HAREKETSIZ,
    ONERI_BEKLIYOR,
    PLAN_ONAYSIZ,
    YENI_FIRSAT,
)
from app.core.kullanici_dili import KULLANICI_DILI_KURALLARI
from app.core.llm import yedekli_zincir
from app.models.hesap import ROL_GENC

logger = logging.getLogger("zemin360.canlilik")


@dataclass(frozen=True)
class HatirlatmaBaglami:
    """Metnin ihtiyaç duyduğu her şey; tamamen yapılandırılmış (LLM girdisi de bu)."""

    tur: str
    alici: str  # "genc" | "kurum"
    gun: int  # kaç gündür hareketsiz / gecikmiş
    karsi_ad: str  # karşı tarafın adı (gence firmanın, firmaya gencin adı)
    adim: str | None = None  # adim_gecikti ve isbirligi_hareketsiz: adımın adı
    sayi: int = 1  # oneri_bekliyor: kaç öneri bekliyor
    sektor: str | None = None  # yeni_firsat
    # Firma–firma iş birliğinde alıcı genç tarafında olsa da firmadır ("siz").
    alici_firma: bool = False

    @property
    def siz(self) -> bool:
        """Firmaya "siz", gence "sen" (docs/icerik-rehberi.md § 3)."""
        return self.alici != ROL_GENC or self.alici_firma


def _gun(gun: int) -> str:
    return "bir haftadır" if gun == 7 else f"{gun} gündür"


def sablon_metni(b: HatirlatmaBaglami) -> str:
    """Türün sabit metni; LLM yoksa hatırlatma bununla gider. Firmaya "siz", gence "sen"."""
    if b.tur == ONERI_BEKLIYOR:
        return (
            f"İhtiyacınız için {b.sayi} aday {_gun(b.gun)} yanıt bekliyor; “Neden uygun?” "
            "açıklamalarına göz atmak birkaç dakika sürer."
        )
    if b.tur == ILGI_YANITSIZ_1:
        if b.siz:
            return (
                f"{b.karsi_ad} {_gun(b.gun)} yanıtınızı bekliyor; kabul etmeniz de "
                "etmemeniz de onlara yol gösterir."
            )
        return (
            f"{b.karsi_ad} {_gun(b.gun)} yanıtını bekliyor; kabul etmen de etmemen de "
            "onlara yol gösterir."
        )
    if b.tur == ILGI_YANITSIZ_2:
        if b.alici == ROL_GENC:
            ek = (
                "yanıtınızı bekliyor. Bu son hatırlatma; kabul etmeniz de etmemeniz de"
                if b.siz
                else "yanıtını bekliyor. Bu son hatırlatma; kabul etmen de etmemen de"
            )
            return f"{b.karsi_ad} {_gun(b.gun)} {ek} onlara yol gösterir."
        return (
            f"{b.karsi_ad} {_gun(b.gun)} yanıt vermedi; bu arada diğer adaylara da bakabilirsiniz."
        )
    if b.tur == PLAN_ONAYSIZ:
        onay = "sizin onayınızla" if b.siz else "senin onayınla"
        return f"{b.karsi_ad} ile planınız {_gun(b.gun)} onay bekliyor; {onay} iş birliği başlar."
    if b.tur == ISBIRLIGI_HAREKETSIZ:
        sonraki = f" Sıradaki adım “{b.adim}”." if b.adim else ""
        return f"{b.karsi_ad} ile iş birliğinizde {_gun(b.gun)} hareket yok.{sonraki}"
    if b.tur == ADIM_GECIKTI:
        eylem = "tamamlandıysa işaretleyin, değilse" if b.siz else "tamamlandıysa işaretle, değilse"
        return (
            f"“{b.adim}” adımının hedef tarihi {b.gun} gün geçti; {eylem} {b.karsi_ad} ile konuşun."
        )
    if b.tur == GENC_ILGISI_YANITSIZ:
        # Firmaya "siz" (docs/icerik-rehberi.md § 3).
        return (
            f"{b.karsi_ad} {_gun(b.gun)} ihtiyacınızla ilgili yanıtınızı bekliyor. "
            "İlgileniyorsanız karşılıklı ilgiyi başlatabilir ya da “Şimdilik değil” "
            "diyebilirsiniz."
        )
    if b.tur == YENI_FIRSAT:
        alan = f" ({b.sektor})" if b.sektor else ""
        # Genç önerilmiş fırsatı zaten görüyor (docs/kararlar.md G1): ad gizlenmez.
        return (
            f"{b.karsi_ad}{alan} yeni bir fırsat açtı; kartına uyuyor. Kanıt eklemek "
            "kartını öne çıkarır."
        )
    raise ValueError(f"Bilinmeyen Canlılık türü: {b.tur}")


# --- Kişiye özel metin (§ 5) — kesilebilir -------------------------------------------------
#
# Hızlı katman, tek çağrı. Girdi tamamen yapılandırılmış; çıktı şablonun
# anlamını koruyan, daha kişisel en fazla iki cümle. Kurala uymayan çıktı
# (boş, uzun, e-posta, girdide olmayan sayı) kullanılmaz: şablon gider.

KISISEL_EN_UZUN = 280

KISISEL_TALIMAT = """Zemin360'ta firmalar ile genç yetenekler arasındaki bağlantıların
sessizce ölmemesi için kısa, kişiye özel hatırlatmalar yazıyorsun.

Sana bir hatırlatmanın yapılandırılmış bilgisi ve anlamı aynı olan sade bir taslak veriliyor.
Taslağı alıcıya hitap eden, sıcak ama resmî olmayan bir dille EN FAZLA İKİ CÜMLEYLE yeniden yaz.

Kurallar:
- Taslaktaki bilgileri (adlar, gün sayısı, adım adı, öneri sayısı) AYNEN koru; yeni bilgi,
  sayı, tarih ya da söz EKLEME.
- Taslağın ANLAMINI değiştirme: "hedef tarihi N gün geçti" ile "N gün geçti" aynı şey değildir;
  kimin neyi beklediğini ve neyin geciktiğini taslaktaki gibi söyle.
- Dolgu cümlesi yazma ("sistem üzerinden", "süreci kolayca ilerletebilirsin" gibi).
- Suçlama, baskı ya da ceza dili kullanma ("ihmal", "hâlâ", "maalesef" gibi); destekleyici ol.
- Bir sonraki adımı açıkça söyle (onayla, işaretle, göz at gibi).
- E-posta adresi, bağlantı, emoji, başlık ya da madde işareti kullanma.
- Girdideki "Hitap" alanına uy: "sen" ise sen diye (gence), "siz" ise siz diye (firmaya)
  hitap et. Taslak da bu hitapla yazılmıştır; hitabı değiştirme. Düz, sade Türkçe."""
KISISEL_TALIMAT += KULLANICI_DILI_KURALLARI

KISISEL_SABLON = ChatPromptTemplate.from_messages(
    [
        ("system", KISISEL_TALIMAT),
        (
            "human",
            "Tür: {tur}\nAlıcı: {alici}\nHitap: {hitap}\nKarşı taraf: {karsi_ad}\nGün: {gun}\n"
            "Adım: {adim}\nÖneri sayısı: {sayi}\nSektör: {sektor}\n\nTaslak: {taslak}",
        ),
    ]
)

_SAYI = re.compile(r"\d+")


def kisisel_metin_gecerli_mi(metin: str, girdi: str) -> bool:
    """Boş değil, kısa, e-posta yok; çıktıdaki her sayı girdide de var."""
    if not metin or len(metin) > KISISEL_EN_UZUN or "@" in metin:
        return False
    return set(_SAYI.findall(metin)) <= set(_SAYI.findall(girdi))


@lru_cache
def _kisisel_zincir() -> Runnable:
    return yedekli_zincir(
        "hizli", "canlilik_hatirlatma", lambda m: KISISEL_SABLON | m | StrOutputParser()
    )


# Yalnızca şablonla giden türler. İstem artık alıcının hitabını ("sen" / "siz")
# girdiden alıyor; şu an şablona zorlanan tür yok, küme gerektiğinde kullanılır.
YALNIZ_SABLON: frozenset[str] = frozenset()


async def kisisel_metin(b: HatirlatmaBaglami) -> str | None:
    """Kişiye özel metin; kullanılamazsa None (çağıran şablona düşer). Hata yutulur."""
    taslak = sablon_metni(b)
    girdiler = {
        "tur": b.tur,
        "alici": "firma" if b.siz else "genç",
        "hitap": "siz" if b.siz else "sen",
        "karsi_ad": b.karsi_ad or "-",
        "gun": b.gun,
        "adim": b.adim or "-",
        "sayi": b.sayi,
        "sektor": b.sektor or "-",
        "taslak": taslak,
    }
    try:
        metin = await _kisisel_zincir().ainvoke(girdiler)
    except Exception:
        logger.warning("Canlılık metni üretilemedi (%s); şablon kullanılacak", b.tur, exc_info=True)
        return None
    metin = " ".join(metin.split())
    if not kisisel_metin_gecerli_mi(metin, " ".join(str(v) for v in girdiler.values())):
        logger.info("Canlılık metni kurala uymadı (%s); şablon kullanılacak: %s", b.tur, metin)
        return None
    return metin


async def metin_uret(b: HatirlatmaBaglami) -> str:
    """Hatırlatma metni: önce kişiye özel, olmazsa şablon. Asla boş dönmez."""
    if b.tur in YALNIZ_SABLON:
        return sablon_metni(b)
    return await kisisel_metin(b) or sablon_metni(b)
