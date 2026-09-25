"""Eşleşme durum makinesi (docs/faz-b-kimlik-ve-dongu.md § 5).

Geçiş kuralı tek yerde ve saf: uç noktalar yalnızca `gecis()`'in söylediğini
uygular (iş birliği aç, aktivite tarihini güncelle…). Tablo
tests/test_eslesme_durumu.py'de birebir sabitlenmiş.

    onerildi ──ilgileniyorum (kurum)──▶ ilgileniliyor ──kabul (genç)──▶ kabul_edildi
                                                    └──red (genç)────▶ reddedildi

Aynı geçişin tekrarı (çift tıklama) hata değil: sonuç `degisti=False` döner
ve uç nokta yan etkiyi tekrarlamaz. Tablo dışındaki her geçiş
`GecersizGecis` — uç noktada 409, mevcut durumu söyleyerek.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.eslestirme import (
    DURUM_ILGILENILIYOR,
    DURUM_KABUL_EDILDI,
    DURUM_ONERILDI,
    DURUM_REDDEDILDI,
)
from app.models.hesap import ROL_GENC, ROL_KURUM

OLAY_ILGILENIYORUM = "ilgileniyorum"
OLAY_KABUL = "kabul"
OLAY_RED = "red"

# (olay) → (kim yapar, hangi durumdan, hangi duruma)
GECISLER: dict[str, tuple[str, str, str]] = {
    OLAY_ILGILENIYORUM: (ROL_KURUM, DURUM_ONERILDI, DURUM_ILGILENILIYOR),
    OLAY_KABUL: (ROL_GENC, DURUM_ILGILENILIYOR, DURUM_KABUL_EDILDI),
    OLAY_RED: (ROL_GENC, DURUM_ILGILENILIYOR, DURUM_REDDEDILDI),
}

DURUM_ETIKETLERI = {
    DURUM_ONERILDI: "önerildi",
    DURUM_ILGILENILIYOR: "kurum ilgileniyor, gencin yanıtı bekleniyor",
    DURUM_KABUL_EDILDI: "kabul edildi",
    DURUM_REDDEDILDI: "reddedildi",
}

OLAY_ETIKETLERI = {
    OLAY_ILGILENIYORUM: "ilgi bildirilemez",
    OLAY_KABUL: "kabul edilemez",
    OLAY_RED: "reddedilemez",
}


class GecersizGecis(Exception):
    """Tablo dışı geçiş. Mesaj kullanıcıya olduğu gibi gösterilebilir."""

    def __init__(self, durum: str, olay: str):
        self.durum, self.olay = durum, olay
        etiket = DURUM_ETIKETLERI.get(durum, durum)
        super().__init__(f"Bu eşleşme şu an '{etiket}' durumunda; {OLAY_ETIKETLERI[olay]}.")


class RolUygunDegil(Exception):
    """Olayı bu rol yapamaz. Uç noktalar rolü zaten süzüyor; bu bir güvence."""


@dataclass(frozen=True)
class GecisSonucu:
    durum: str
    # False: aynı geçişin tekrarı — yan etki yok, aktivite tarihi değişmez.
    degisti: bool


def gecis(durum: str, olay: str, rol: str) -> GecisSonucu:
    yapan, kaynak, hedef = GECISLER[olay]
    if rol != yapan:
        raise RolUygunDegil(olay)
    if durum == kaynak:
        return GecisSonucu(hedef, degisti=True)
    if durum == hedef:
        return GecisSonucu(hedef, degisti=False)
    raise GecersizGecis(durum, olay)
