"""Canlılık Ajanı — pasiflik ve tekrar kuralları (docs/faz-d-canlilik.md § 1-3).

Saf fonksiyonlar: veritabanı ve LLM yok. Tarama (app/api/canlilik.py) aday
kayıtları toplar, bu modüle sorar, cevabı uygular. Tablo
tests/test_canlilik_kurallari.py'de birebir sabitlenmiş.

Pasiflik saklanmaz; mevcut alanlardan okuma anında hesaplanır:
- hareket: eşleşmenin `son_aktivite_tarihi` (Faz B-C her geçişte günceller),
- gecikme: milestone'un `hedef_tarih`'i.

Canlılık hiçbir kaydın durumunu değiştirmez: hatırlatır, karar vermez.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.agents.eslestirme import DURUM_GENC_ILGILENDI, DURUM_ILGILENILIYOR, DURUM_ONERILDI
from app.agents.takip_durumu import ISBIRLIGI_AKTIF, ISBIRLIGI_PLAN_BEKLIYOR
from app.models.hesap import ROL_GENC, ROL_KURUM

ONERI_BEKLIYOR = "oneri_bekliyor"
ILGI_YANITSIZ_1 = "ilgi_yanitsiz_1"
ILGI_YANITSIZ_2 = "ilgi_yanitsiz_2"
PLAN_ONAYSIZ = "plan_onaysiz"
ISBIRLIGI_HAREKETSIZ = "isbirligi_hareketsiz"
ADIM_GECIKTI = "adim_gecikti"
YENI_FIRSAT = "yeni_firsat"
# Genç ilgi gösterdi, firma yanıt vermedi (docs/plans/genc-akisi.md § 7.1).
GENC_ILGISI_YANITSIZ = "genc_ilgisi_yanitsiz"

TURLER = (
    ONERI_BEKLIYOR,
    ILGI_YANITSIZ_1,
    ILGI_YANITSIZ_2,
    PLAN_ONAYSIZ,
    ISBIRLIGI_HAREKETSIZ,
    ADIM_GECIKTI,
    YENI_FIRSAT,
    GENC_ILGISI_YANITSIZ,
)

# Eşikler (gün) — onaylı tablo, § 1. Tek yer; .env'den değişmez (demo için
# scripts/zamani_geri_al.py kayıtların zamanını geri çeker).
ESIKLER: dict[str, int] = {
    ONERI_BEKLIYOR: 7,
    ILGI_YANITSIZ_1: 3,
    ILGI_YANITSIZ_2: 10,
    PLAN_ONAYSIZ: 5,
    ISBIRLIGI_HAREKETSIZ: 14,
    ADIM_GECIKTI: 1,  # hedef tarihten sonra
    # Genç akışı (plan § 0, karar 6): firmaya, tek kademe, sabit.
    GENC_ILGISI_YANITSIZ: 5,
}
# Yeni fırsat (§ 2): son bu kadar günde açılmış ihtiyaç kartı…
FIRSAT_YENI_IHTIYAC_GUN = 7
# …en az bu kadar gün önce oluşturulmuş ("eski") bir yetenek kartına önerildiyse.
FIRSAT_ESKI_KART_GUN = 14


@dataclass(frozen=True)
class Hatirlatma:
    """Tarama bu kayıt için kime, hangi türde hatırlatma bırakmalı."""

    tur: str
    alici: str  # "genc" | "kurum"
    milestone_id: object | None = None  # adim_gecikti'de hangi adım


def gecen_gun(an: dt.datetime, simdi: dt.datetime) -> int:
    """Tam gün sayısı (aşağı yuvarlanır): 2 gün 23 saat = 2 gün."""
    return max(0, (simdi - an).days)


# --- Eşleşme -------------------------------------------------------------------------------


def eslesme_hatirlatmalari(durum: str, hareketsiz_gun: int) -> list[Hatirlatma]:
    """`onerildi`, `ilgileniliyor` ve `genc_ilgilendi` eşleşmeler; diğerleri hatırlatılmaz."""
    if durum == DURUM_ONERILDI:
        if hareketsiz_gun >= ESIKLER[ONERI_BEKLIYOR]:
            return [Hatirlatma(ONERI_BEKLIYOR, ROL_KURUM)]
        return []
    if durum == DURUM_ILGILENILIYOR:
        # İkinci kademe birinciyi kapsar: 12. günde ilk tarama yalnızca
        # ikinciyi gönderir, "3 gündür" diyen birinciyi değil.
        if hareketsiz_gun >= ESIKLER[ILGI_YANITSIZ_2]:
            return [Hatirlatma(ILGI_YANITSIZ_2, ROL_GENC), Hatirlatma(ILGI_YANITSIZ_2, ROL_KURUM)]
        if hareketsiz_gun >= ESIKLER[ILGI_YANITSIZ_1]:
            return [Hatirlatma(ILGI_YANITSIZ_1, ROL_GENC)]
    if durum == DURUM_GENC_ILGILENDI:
        # Tek kademe: firma bir kez hatırlatılır; yanıt vermezse kayıt korunur
        # (karar 14), ısrar edilmez.
        if hareketsiz_gun >= ESIKLER[GENC_ILGISI_YANITSIZ]:
            return [Hatirlatma(GENC_ILGISI_YANITSIZ, ROL_KURUM)]
    return []


# --- İş birliği ----------------------------------------------------------------------------


@dataclass(frozen=True)
class AdimBilgisi:
    id: object
    hedef_tarih: dt.date | None
    genc_isaretledi: bool
    kurum_isaretledi: bool

    @property
    def tamamlandi(self) -> bool:
        return self.genc_isaretledi and self.kurum_isaretledi


def gecikme_gunu(hedef_tarih: dt.date | None, tamamlandi: bool, bugun: dt.date) -> int:
    """Hedeften bu yana kaç gün (tamamlanmamış adım için; yoksa 0)."""
    if hedef_tarih is None or tamamlandi:
        return 0
    return max(0, (bugun - hedef_tarih).days)


def isbirligi_hatirlatmalari(
    *,
    durum: str,
    hareketsiz_gun: int,
    genc_plan_onayi: bool,
    kurum_plan_onayi: bool,
    adimlar: list[AdimBilgisi],
    bugun: dt.date,
) -> list[Hatirlatma]:
    """`plan_bekliyor` ve `aktif` iş birlikleri; `tamamlandi` hatırlatılmaz.

    Öncelik (§ 1): gecikmiş adım hatırlatması alan kişiye aynı taramada ayrıca
    "hareket yok" gitmez — gecikmiş adım zaten hareketsizlik demek.
    """
    if durum == ISBIRLIGI_PLAN_BEKLIYOR:
        if hareketsiz_gun < ESIKLER[PLAN_ONAYSIZ]:
            return []
        onaysizlar = [
            rol
            for rol, onay in ((ROL_GENC, genc_plan_onayi), (ROL_KURUM, kurum_plan_onayi))
            if not onay
        ]
        return [Hatirlatma(PLAN_ONAYSIZ, rol) for rol in onaysizlar]

    if durum != ISBIRLIGI_AKTIF:
        return []

    sonuc: list[Hatirlatma] = []
    for adim in adimlar:
        if gecikme_gunu(adim.hedef_tarih, adim.tamamlandi, bugun) < ESIKLER[ADIM_GECIKTI]:
            continue
        for rol, isaretledi in (
            (ROL_GENC, adim.genc_isaretledi),
            (ROL_KURUM, adim.kurum_isaretledi),
        ):
            if not isaretledi:
                sonuc.append(Hatirlatma(ADIM_GECIKTI, rol, adim.id))

    if hareketsiz_gun >= ESIKLER[ISBIRLIGI_HAREKETSIZ]:
        gecikmeden_haberdar = {h.alici for h in sonuc}
        for rol in (ROL_GENC, ROL_KURUM):
            if rol not in gecikmeden_haberdar:
                sonuc.append(Hatirlatma(ISBIRLIGI_HAREKETSIZ, rol))
    return sonuc


# --- Yeni fırsat ---------------------------------------------------------------------------


def firsat_mi(
    ihtiyac_olusturma: dt.datetime, kart_olusturma: dt.datetime, simdi: dt.datetime
) -> bool:
    """Yeni ihtiyaç (son 7 gün) eski bir karta (en az 14 günlük) önerildi mi?"""
    return (
        gecen_gun(ihtiyac_olusturma, simdi) < FIRSAT_YENI_IHTIYAC_GUN
        and gecen_gun(kart_olusturma, simdi) >= FIRSAT_ESKI_KART_GUN
    )


# --- Tekrar kuralı (§ 3) -------------------------------------------------------------------


def tekrar_mi(tur: str, son_olay: dt.datetime | None, son_aktivite: dt.datetime | None) -> bool:
    """Aynı anahtar için bu dönemde zaten hatırlatıldı mı?

    Dönem = son hareketten bu yana. Olay son hareketten SONRA yazılmışsa bu
    dönem hatırlatıldı demektir; biri hareket edince dönem kapanır ve
    hareketsizlik yeniden eşiği aşarsa yeni hatırlatma gidebilir.
    Yeni fırsatın dönemi yok: bir kez gider.
    """
    if son_olay is None:
        return False
    if tur == YENI_FIRSAT or son_aktivite is None:
        return True
    return son_olay >= son_aktivite
