"""Eşleşme durum makinesi (docs/kimlik-ve-dongu.md § 5, docs/kimlik-ve-dongu.md § 5).

Geçiş kuralı tek yerde ve saf: uç noktalar ve servisler yalnızca `gecis()`'in
söylediğini uygular (iş birliği aç, aktivite tarihini güncelle…). Tablo
tests/test_eslesme_durumu.py ve tests/test_ilgi_durumu.py'de birebir sabitlenmiş.

İki kapı var, ayrı sistem değil: ilk ilgiyi kurum da gösterebilir genç de.

    onerildi ──ilgileniyorum (kurum)──▶ ilgileniliyor ──kabul (genç)──▶ kabul_edildi
       │                                             └──red (genç)────▶ reddedildi
       └──genc_ilgi (genç)──▶ genc_ilgilendi ──ilgileniyorum (kurum)──▶ kabul_edildi
                                  ├──simdilik_degil (kurum)──▶ kapandi
                                  └──ilgiyi_geri_cek (genç)──▶ onerildi
    onerildi | genc_ilgilendi | ilgileniliyor ──ihtiyac_kapandi (sistem)──▶ kapandi

Karşılıklı ilgi `kabul_edildi`'dir: genç ilgiyi gösterirken iletişim onayını
verdi, kurum ilgilenince ayrıca onay beklenmez; iş birliği açılır.

Aynı geçişin tekrarı (çift tıklama) hata değil: sonuç `degisti=False` döner
ve uç nokta yan etkiyi tekrarlamaz. Tablo dışındaki her geçiş `GecersizGecis`,
uç noktada 409, mevcut durumu söyleyerek.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.eslestirme import (
    DURUM_GENC_ILGILENDI,
    DURUM_ILGILENILIYOR,
    DURUM_KABUL_EDILDI,
    DURUM_KAPANDI,
    DURUM_ONERILDI,
    DURUM_REDDEDILDI,
)
from app.models.hesap import ROL_GENC, ROL_KURUM

# Kimse adına değil, kuralın kendisi (ihtiyaç kapanınca).
ROL_SISTEM = "sistem"

OLAY_ILGILENIYORUM = "ilgileniyorum"
OLAY_KABUL = "kabul"
OLAY_RED = "red"
OLAY_GENC_ILGI = "genc_ilgi"
OLAY_ILGIYI_GERI_CEK = "ilgiyi_geri_cek"
OLAY_SIMDILIK_DEGIL = "simdilik_degil"
OLAY_IHTIYAC_KAPANDI = "ihtiyac_kapandi"

# (olay, kaynak durum) → (kim yapar, hedef durum)
GECISLER: dict[tuple[str, str], tuple[str, str]] = {
    (OLAY_ILGILENIYORUM, DURUM_ONERILDI): (ROL_KURUM, DURUM_ILGILENILIYOR),
    (OLAY_KABUL, DURUM_ILGILENILIYOR): (ROL_GENC, DURUM_KABUL_EDILDI),
    (OLAY_RED, DURUM_ILGILENILIYOR): (ROL_GENC, DURUM_REDDEDILDI),
    # Gençten ilgi (docs/kimlik-ve-dongu.md § 5)
    (OLAY_GENC_ILGI, DURUM_ONERILDI): (ROL_GENC, DURUM_GENC_ILGILENDI),
    (OLAY_ILGIYI_GERI_CEK, DURUM_GENC_ILGILENDI): (ROL_GENC, DURUM_ONERILDI),
    (OLAY_ILGILENIYORUM, DURUM_GENC_ILGILENDI): (ROL_KURUM, DURUM_KABUL_EDILDI),
    (OLAY_SIMDILIK_DEGIL, DURUM_GENC_ILGILENDI): (ROL_KURUM, DURUM_KAPANDI),
    # İhtiyaç kapanınca karar verilmemiş kayıtlar kapanır
    (OLAY_IHTIYAC_KAPANDI, DURUM_ONERILDI): (ROL_SISTEM, DURUM_KAPANDI),
    (OLAY_IHTIYAC_KAPANDI, DURUM_GENC_ILGILENDI): (ROL_SISTEM, DURUM_KAPANDI),
    (OLAY_IHTIYAC_KAPANDI, DURUM_ILGILENILIYOR): (ROL_SISTEM, DURUM_KAPANDI),
}

# Olayı kim yapar (her olayın tek bir yapanı var).
OLAYIN_ROLU: dict[str, str] = {olay: rol for (olay, _), (rol, _) in GECISLER.items()}

# 409 cümleleri arayüzde görünür (docs/icerik-rehberi.md).
DURUM_ETIKETLERI = {
    DURUM_ONERILDI: "önerildi",
    DURUM_ILGILENILIYOR: "ilgi iletildi, yanıt bekleniyor",
    DURUM_KABUL_EDILDI: "karşılıklı ilgi",
    DURUM_REDDEDILDI: "kapandı",
    DURUM_GENC_ILGILENDI: "ilgi iletildi, yanıt bekleniyor",
    DURUM_KAPANDI: "kapandı",
}

OLAY_ETIKETLERI = {
    OLAY_ILGILENIYORUM: "ilgi bildirilemez",
    OLAY_KABUL: "kabul edilemez",
    OLAY_RED: "reddedilemez",
    OLAY_GENC_ILGI: "ilgi gösterilemez",
    OLAY_ILGIYI_GERI_CEK: "ilgi geri çekilemez",
    OLAY_SIMDILIK_DEGIL: "kapatılamaz",
    OLAY_IHTIYAC_KAPANDI: "kapatılamaz",
}


class GecersizGecis(Exception):
    """Tablo dışı geçiş. Mesaj kullanıcıya olduğu gibi gösterilebilir."""

    def __init__(self, durum: str, olay: str):
        self.durum, self.olay = durum, olay
        etiket = DURUM_ETIKETLERI.get(durum, durum)
        super().__init__(f"Bu eşleşme şu an “{etiket}” durumunda; {OLAY_ETIKETLERI[olay]}.")


class RolUygunDegil(Exception):
    """Olayı bu rol yapamaz. Uç noktalar rolü zaten süzüyor; bu bir güvence."""


@dataclass(frozen=True)
class GecisSonucu:
    durum: str
    # False: aynı geçişin tekrarı — yan etki yok, aktivite tarihi değişmez.
    degisti: bool


def gecis(durum: str, olay: str, rol: str, baslatan: str | None = None) -> GecisSonucu:
    """`baslatan`: ilk ilgiyi kim gösterdi (eşleşmenin `baslatan` alanı).

    Yalnızca bir yerde fark eder: kurumun `kabul_edildi` bir eşleşmeye yeniden
    "ilgileniyorum" demesi. Eşleşme karşılıklı ilgiyle açıldıysa (genç başlattı)
    bu, kurumun kendi geçişinin tekrarıdır (200). Kurum başlattıysa `kabul_edildi`
    gencin kabulüdür, kurumun geçişi değil: 409.
    """
    if rol != OLAYIN_ROLU[olay]:
        raise RolUygunDegil(olay)
    kural = GECISLER.get((olay, durum))
    if kural is not None:
        return GecisSonucu(kural[1], degisti=True)
    if _tekrar_mi(durum, olay, baslatan):
        return GecisSonucu(durum, degisti=False)
    raise GecersizGecis(durum, olay)


def _tekrar_mi(durum: str, olay: str, baslatan: str | None) -> bool:
    """Durum, bu olayın bir geçişinin hedefi mi (aynı geçişin tekrarı)?"""
    if olay == OLAY_ILGILENIYORUM and durum == DURUM_KABUL_EDILDI:
        return baslatan == ROL_GENC
    return any(o == olay and hedef == durum for (o, _), (_, hedef) in GECISLER.items())


# --- Gençten ilgi: açıklık (backend'de de uygulanır) ---------------------------------------

IHTIYAC_ACIK = "acik"
IHTIYAC_KAPALI = "Bu fırsat kapandı."


def ilgi_engeli(ihtiyac_durumu: str) -> str | None:
    """Aday bu eşleşmeye ilgi gösterebilir mi? Gösteremiyorsa nedeni (409).

    Yalnızca açık ihtiyaç. Alakasız aday için zaten öneri kaydı yazılmıyor
    (giriş kararı benzerlik tabanında); skor ilgiyi engellemez.
    """
    if ihtiyac_durumu != IHTIYAC_ACIK:
        return IHTIYAC_KAPALI
    return None
