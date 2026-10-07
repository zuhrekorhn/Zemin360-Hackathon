"""Takip Ajanı durum makineleri (docs/takip.md § 3).

İki kural, ikisi de saf fonksiyon; uç noktalar yalnızca sonucu uygular
(`eslesme_durumu.gecis` deseni). Tablo
tests/test_takip_durumu.py'de birebir sabitlenmiş.

    Plan:       plan_bekliyor ──(iki taraf onaylar)──▶ aktif ──(son adım)──▶ tamamlandi
                plan_bekliyor | aktif ──(bir taraf sonlandırır)──▶ sonlandi (geri açılmaz)
    Milestone:  bekliyor ──(genç + kurum işaretler)──▶ tamamlandi

Ajan karar vermez: tamamlanma, iki tarafın işaretlerinden çıkan bir kural.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass, replace

from app.models.hesap import ROL_GENC, ROL_KURUM

ISBIRLIGI_PLAN_BEKLIYOR = "plan_bekliyor"
ISBIRLIGI_AKTIF = "aktif"
ISBIRLIGI_TAMAMLANDI = "tamamlandi"
# Erken sonlanma (docs/kararlar.md T1): görüşmeden sonra "şimdilik değil"
# olağan bir sonuç. Tamamlanmış sayılmaz (pilot bonusu yalnızca `tamamlandi`).
ISBIRLIGI_SONLANDI = "sonlandi"
SONLANMA_NEDENLERI: tuple[str, ...] = (
    "karar_olumsuz",
    "baska_yoldan_ilerlendi",
    "iletisim_kurulamadi",
)

MILESTONE_BEKLIYOR = "bekliyor"
MILESTONE_TAMAMLANDI = "tamamlandi"

PLAN_DUZENLE = "duzenle"  # milestone ekle / düzenle / sil, plan öner
PLAN_ONAYLA = "onayla"

ISARETLE = "isaretle"
ISARETI_GERI_AL = "isareti_geri_al"

TARAFLAR = (ROL_GENC, ROL_KURUM)

PLAN_KILITLI = "Plan iki tarafça onaylandı; artık değiştirilemez."
ISBIRLIGI_BITTI = "İş birliği tamamlandı; değişiklik yapılamaz."
SUREC_SONLANDI = "Bu süreç sonlandırıldı; değişiklik yapılamaz."
PLAN_BOS = "Önce en az bir adım eklenmeli."
PLAN_ONAYSIZ = "Plan iki tarafça onaylanmadan adımlar işaretlenemez."
ADIM_KAPANDI = "Bu adım iki tarafça tamamlandı; işaret geri alınamaz."


class GecersizTakipGecisi(Exception):
    """Kural dışı eylem; mesaj kullanıcıya olduğu gibi gösterilebilir (409)."""


class RolUygunDegil(Exception):
    """Yalnızca iki taraf (genç, kurum) eylem yapar. Uçlar zaten süzüyor."""


def _taraf_mi(rol: str) -> None:
    if rol not in TARAFLAR:
        raise RolUygunDegil(rol)


def _kapali_degil(durum: str) -> None:
    """Tamamlanmış ya da sonlandırılmış iş birliğinde hiçbir eylem yapılmaz."""
    if durum == ISBIRLIGI_TAMAMLANDI:
        raise GecersizTakipGecisi(ISBIRLIGI_BITTI)
    if durum == ISBIRLIGI_SONLANDI:
        raise GecersizTakipGecisi(SUREC_SONLANDI)


# --- Plan -----------------------------------------------------------------------------


@dataclass(frozen=True)
class PlanDurumu:
    durum: str
    genc_onayi: bool
    kurum_onayi: bool


@dataclass(frozen=True)
class PlanSonucu:
    durum: PlanDurumu
    # False: aynı onayın tekrarı — yan etki (bildirim) yok.
    degisti: bool


def plan_gecisi(mevcut: PlanDurumu, olay: str, rol: str, *, milestone_sayisi: int) -> PlanSonucu:
    _taraf_mi(rol)
    _kapali_degil(mevcut.durum)
    if mevcut.durum != ISBIRLIGI_PLAN_BEKLIYOR:
        raise GecersizTakipGecisi(PLAN_KILITLI)

    if olay == PLAN_DUZENLE:
        # Plan değişti: iki onay da sıfırlanır, herkes son hâli onaylasın.
        return PlanSonucu(PlanDurumu(ISBIRLIGI_PLAN_BEKLIYOR, False, False), degisti=True)

    if olay != PLAN_ONAYLA:
        raise ValueError(olay)
    if milestone_sayisi < 1:
        raise GecersizTakipGecisi(PLAN_BOS)
    kendi_onayi = mevcut.genc_onayi if rol == ROL_GENC else mevcut.kurum_onayi
    if kendi_onayi:
        return PlanSonucu(mevcut, degisti=False)
    yeni = (
        replace(mevcut, genc_onayi=True) if rol == ROL_GENC else replace(mevcut, kurum_onayi=True)
    )
    if yeni.genc_onayi and yeni.kurum_onayi:
        yeni = replace(yeni, durum=ISBIRLIGI_AKTIF)
    return PlanSonucu(yeni, degisti=True)


# --- Milestone işareti ------------------------------------------------------------------


@dataclass(frozen=True)
class Isaretler:
    genc: bool
    kurum: bool

    @property
    def tamamlandi(self) -> bool:
        return self.genc and self.kurum


@dataclass(frozen=True)
class IsaretSonucu:
    isaretler: Isaretler
    degisti: bool

    @property
    def tamamlandi(self) -> bool:
        return self.isaretler.tamamlandi


def isaret_gecisi(isbirligi_durumu: str, mevcut: Isaretler, olay: str, rol: str) -> IsaretSonucu:
    _taraf_mi(rol)
    _kapali_degil(isbirligi_durumu)
    if isbirligi_durumu != ISBIRLIGI_AKTIF:
        raise GecersizTakipGecisi(PLAN_ONAYSIZ)

    kendi = mevcut.genc if rol == ROL_GENC else mevcut.kurum
    if olay == ISARETLE:
        if kendi:
            return IsaretSonucu(mevcut, degisti=False)
        yeni = replace(mevcut, genc=True) if rol == ROL_GENC else replace(mevcut, kurum=True)
        return IsaretSonucu(yeni, degisti=True)

    if olay != ISARETI_GERI_AL:
        raise ValueError(olay)
    if mevcut.tamamlandi:
        raise GecersizTakipGecisi(ADIM_KAPANDI)
    if not kendi:
        return IsaretSonucu(mevcut, degisti=False)
    yeni = replace(mevcut, genc=False) if rol == ROL_GENC else replace(mevcut, kurum=False)
    return IsaretSonucu(yeni, degisti=True)


# --- Erken sonlanma ---------------------------------------------------------------------


def sonlanma_gecisi(isbirligi_durumu: str, rol: str) -> bool:
    """Bir taraf süreci sonlandırır. Döner: değişti mi (False: zaten sonlanmış,
    tekrar yan etkisiz). Tamamlanmış iş birliği sonlandırılamaz; `sonlandi` geri
    açılmaz (diğer geçişler `_kapali_degil` ile 409)."""
    _taraf_mi(rol)
    if isbirligi_durumu == ISBIRLIGI_SONLANDI:
        return False
    if isbirligi_durumu == ISBIRLIGI_TAMAMLANDI:
        raise GecersizTakipGecisi(ISBIRLIGI_BITTI)
    return True


# --- Tamamlanma ve gecikme --------------------------------------------------------------


def isbirligi_tamamlandi_mi(milestone_tamamlandi: Sequence[bool]) -> bool:
    """Kural: en az bir adım var ve hepsi iki tarafça tamamlandı."""
    return len(milestone_tamamlandi) > 0 and all(milestone_tamamlandi)


def gecikmis_mi(hedef_tarih: dt.date | None, tamamlandi: bool, bugun: dt.date) -> bool:
    """Okuma anında hesaplanır, saklanmaz (Doğrulama zaman aşımıyla aynı desen)."""
    return hedef_tarih is not None and not tamamlandi and hedef_tarih < bugun
