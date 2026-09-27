"""Canlılık Ajanı — hatırlatma metinleri (docs/faz-d-canlilik.md § 5).

Her türün sabit bir şablon metni var: LLM kişiselleştirmesi (kesilebilir)
yanıt vermezse ya da kesilirse hatırlatma bu metinle aynen gider, asla
kaybolmaz. Metinde ad olabilir, e-posta olmaz; dil nötr ve destekleyici.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.canlilik_kurallari import (
    ADIM_GECIKTI,
    ILGI_YANITSIZ_1,
    ILGI_YANITSIZ_2,
    ISBIRLIGI_HAREKETSIZ,
    ONERI_BEKLIYOR,
    PLAN_ONAYSIZ,
    YENI_FIRSAT,
)
from app.models.hesap import ROL_GENC


@dataclass(frozen=True)
class HatirlatmaBaglami:
    """Metnin ihtiyaç duyduğu her şey; tamamen yapılandırılmış (LLM girdisi de bu)."""

    tur: str
    alici: str  # "genc" | "kurum"
    gun: int  # kaç gündür hareketsiz / gecikmiş
    karsi_ad: str  # karşı tarafın adı (genç için kurum, kurum için genç)
    adim: str | None = None  # adim_gecikti ve isbirligi_hareketsiz: adımın adı
    sayi: int = 1  # oneri_bekliyor: kaç öneri bekliyor
    sektor: str | None = None  # yeni_firsat


def _gun(gun: int) -> str:
    return "bir haftadır" if gun == 7 else f"{gun} gündür"


def sablon_metni(b: HatirlatmaBaglami) -> str:
    """Türün sabit metni; LLM yoksa hatırlatma bununla gider."""
    if b.tur == ONERI_BEKLIYOR:
        return (
            f"İhtiyaç kartın için {b.sayi} öneri {_gun(b.gun)} yanıt bekliyor; "
            "gerekçelere göz atmak birkaç dakika sürer."
        )
    if b.tur == ILGI_YANITSIZ_1:
        return (
            f"{b.karsi_ad} {_gun(b.gun)} yanıtını bekliyor; kabul ya da ret, ikisi de "
            "onlara yol gösterir."
        )
    if b.tur == ILGI_YANITSIZ_2:
        if b.alici == ROL_GENC:
            return (
                f"{b.karsi_ad} {_gun(b.gun)} yanıtını bekliyor. Bu son hatırlatma; kabul ya "
                "da ret, ikisi de onlara yol gösterir."
            )
        return (
            f"{b.karsi_ad} {_gun(b.gun)} yanıt vermedi; bu arada diğer önerilere de bakabilirsin."
        )
    if b.tur == PLAN_ONAYSIZ:
        return (
            f"{b.karsi_ad} ile planınız {_gun(b.gun)} onay bekliyor; senin onayınla iş "
            "birliği başlar."
        )
    if b.tur == ISBIRLIGI_HAREKETSIZ:
        sonraki = f" Sıradaki adım “{b.adim}”." if b.adim else ""
        return f"{b.karsi_ad} ile iş birliğinizde {_gun(b.gun)} hareket yok.{sonraki}"
    if b.tur == ADIM_GECIKTI:
        return (
            f"“{b.adim}” adımının hedef tarihi {b.gun} gün geçti; tamamlandıysa işaretle, "
            f"değilse {b.karsi_ad} ile konuşun."
        )
    if b.tur == YENI_FIRSAT:
        alan = f" ({b.sektor})" if b.sektor else ""
        return f"Kartına uyan yeni bir ihtiyaç var{alan}. Kanıt eklemek kartını öne çıkarır."
    raise ValueError(f"Bilinmeyen Canlılık türü: {b.tur}")
