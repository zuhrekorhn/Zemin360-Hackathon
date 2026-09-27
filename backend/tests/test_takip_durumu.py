"""Takip durum makineleri — docs/faz-c-takip.md § 3'teki tablolar, birebir."""

import datetime as dt
import itertools

import pytest

from app.agents.takip_durumu import (
    ADIM_KAPANDI,
    ISARETI_GERI_AL,
    ISARETLE,
    ISBIRLIGI_AKTIF,
    ISBIRLIGI_BITTI,
    ISBIRLIGI_PLAN_BEKLIYOR,
    ISBIRLIGI_TAMAMLANDI,
    PLAN_BOS,
    PLAN_DUZENLE,
    PLAN_KILITLI,
    PLAN_ONAYLA,
    PLAN_ONAYSIZ,
    GecersizTakipGecisi,
    Isaretler,
    PlanDurumu,
    RolUygunDegil,
    gecikmis_mi,
    isaret_gecisi,
    isbirligi_tamamlandi_mi,
    plan_gecisi,
)

BEKLIYOR_ONAYSIZ = PlanDurumu(ISBIRLIGI_PLAN_BEKLIYOR, False, False)

# --- Plan -------------------------------------------------------------------------------


@pytest.mark.parametrize("rol", ["genc", "kurum"])
@pytest.mark.parametrize(
    "onaylar", list(itertools.product([False, True], repeat=2)), ids=lambda o: str(o)
)
def test_duzenleme_iki_onayi_da_sifirlar(rol, onaylar):
    mevcut = PlanDurumu(ISBIRLIGI_PLAN_BEKLIYOR, *onaylar)
    sonuc = plan_gecisi(mevcut, PLAN_DUZENLE, rol, milestone_sayisi=3)
    assert sonuc.durum == BEKLIYOR_ONAYSIZ
    assert sonuc.degisti


def test_ilk_onay_yalnizca_kendi_onayini_yazar():
    sonuc = plan_gecisi(BEKLIYOR_ONAYSIZ, PLAN_ONAYLA, "genc", milestone_sayisi=3)
    assert sonuc.durum == PlanDurumu(ISBIRLIGI_PLAN_BEKLIYOR, True, False)
    assert sonuc.degisti
    sonuc = plan_gecisi(BEKLIYOR_ONAYSIZ, PLAN_ONAYLA, "kurum", milestone_sayisi=3)
    assert sonuc.durum == PlanDurumu(ISBIRLIGI_PLAN_BEKLIYOR, False, True)


@pytest.mark.parametrize(
    "mevcut,rol",
    [
        (PlanDurumu(ISBIRLIGI_PLAN_BEKLIYOR, True, False), "kurum"),
        (PlanDurumu(ISBIRLIGI_PLAN_BEKLIYOR, False, True), "genc"),
    ],
)
def test_ikinci_onay_isbirligini_baslatir(mevcut, rol):
    sonuc = plan_gecisi(mevcut, PLAN_ONAYLA, rol, milestone_sayisi=1)
    assert sonuc.durum == PlanDurumu(ISBIRLIGI_AKTIF, True, True)
    assert sonuc.degisti


def test_ayni_onayin_tekrari_yan_etkisiz():
    mevcut = PlanDurumu(ISBIRLIGI_PLAN_BEKLIYOR, True, False)
    sonuc = plan_gecisi(mevcut, PLAN_ONAYLA, "genc", milestone_sayisi=3)
    assert sonuc.durum == mevcut
    assert not sonuc.degisti


def test_bos_plan_onaylanamaz():
    with pytest.raises(GecersizTakipGecisi, match=PLAN_BOS):
        plan_gecisi(BEKLIYOR_ONAYSIZ, PLAN_ONAYLA, "genc", milestone_sayisi=0)


@pytest.mark.parametrize("olay", [PLAN_DUZENLE, PLAN_ONAYLA])
@pytest.mark.parametrize(
    "durum,mesaj", [(ISBIRLIGI_AKTIF, PLAN_KILITLI), (ISBIRLIGI_TAMAMLANDI, ISBIRLIGI_BITTI)]
)
def test_onaylanmis_ya_da_biten_plan_kilitli(olay, durum, mesaj):
    with pytest.raises(GecersizTakipGecisi, match=mesaj):
        plan_gecisi(PlanDurumu(durum, True, True), olay, "genc", milestone_sayisi=3)


@pytest.mark.parametrize("olay", [PLAN_DUZENLE, PLAN_ONAYLA])
def test_girvak_plana_dokunamaz(olay):
    with pytest.raises(RolUygunDegil):
        plan_gecisi(BEKLIYOR_ONAYSIZ, olay, "girvak", milestone_sayisi=3)


# --- Milestone işareti ------------------------------------------------------------------

ISARETSIZ = Isaretler(genc=False, kurum=False)


@pytest.mark.parametrize(
    "rol,beklenen", [("genc", Isaretler(True, False)), ("kurum", Isaretler(False, True))]
)
def test_ilk_isaret(rol, beklenen):
    sonuc = isaret_gecisi(ISBIRLIGI_AKTIF, ISARETSIZ, ISARETLE, rol)
    assert sonuc.isaretler == beklenen
    assert sonuc.degisti and not sonuc.tamamlandi


@pytest.mark.parametrize(
    "mevcut,rol", [(Isaretler(True, False), "kurum"), (Isaretler(False, True), "genc")]
)
def test_karsi_tarafin_isareti_adimi_tamamlar(mevcut, rol):
    sonuc = isaret_gecisi(ISBIRLIGI_AKTIF, mevcut, ISARETLE, rol)
    assert sonuc.tamamlandi and sonuc.degisti


@pytest.mark.parametrize("rol", ["genc", "kurum"])
def test_kendi_isaretini_tekrarlamak_yan_etkisiz(rol):
    mevcut = Isaretler(genc=rol == "genc", kurum=rol == "kurum")
    sonuc = isaret_gecisi(ISBIRLIGI_AKTIF, mevcut, ISARETLE, rol)
    assert sonuc.isaretler == mevcut and not sonuc.degisti


@pytest.mark.parametrize("rol", ["genc", "kurum"])
def test_kendi_isaretini_geri_alir(rol):
    mevcut = Isaretler(genc=rol == "genc", kurum=rol == "kurum")
    sonuc = isaret_gecisi(ISBIRLIGI_AKTIF, mevcut, ISARETI_GERI_AL, rol)
    assert sonuc.isaretler == ISARETSIZ and sonuc.degisti


def test_karsi_tarafin_isaretini_geri_alamaz():
    """Genç geri al derse yalnızca kendi işaretine bakılır; kurumunki kalır."""
    mevcut = Isaretler(genc=False, kurum=True)
    sonuc = isaret_gecisi(ISBIRLIGI_AKTIF, mevcut, ISARETI_GERI_AL, "genc")
    assert sonuc.isaretler == mevcut and not sonuc.degisti


@pytest.mark.parametrize("rol", ["genc", "kurum"])
def test_tamamlanan_adim_geri_acilmaz(rol):
    with pytest.raises(GecersizTakipGecisi, match=ADIM_KAPANDI):
        isaret_gecisi(ISBIRLIGI_AKTIF, Isaretler(True, True), ISARETI_GERI_AL, rol)
    # İşaretlemenin tekrarı ise zararsız.
    sonuc = isaret_gecisi(ISBIRLIGI_AKTIF, Isaretler(True, True), ISARETLE, rol)
    assert not sonuc.degisti


@pytest.mark.parametrize("olay", [ISARETLE, ISARETI_GERI_AL])
@pytest.mark.parametrize(
    "durum,mesaj",
    [(ISBIRLIGI_PLAN_BEKLIYOR, PLAN_ONAYSIZ), (ISBIRLIGI_TAMAMLANDI, ISBIRLIGI_BITTI)],
)
def test_yalnizca_aktif_isbirliginde_isaret(olay, durum, mesaj):
    with pytest.raises(GecersizTakipGecisi, match=mesaj):
        isaret_gecisi(durum, ISARETSIZ, olay, "genc")


def test_girvak_isaretleyemez():
    with pytest.raises(RolUygunDegil):
        isaret_gecisi(ISBIRLIGI_AKTIF, ISARETSIZ, ISARETLE, "girvak")


# --- Tamamlanma ve gecikme ----------------------------------------------------------------


@pytest.mark.parametrize(
    "adimlar,beklenen",
    [([], False), ([True], True), ([True, True, True], True), ([True, False], False)],
)
def test_tamamlanma_kurali(adimlar, beklenen):
    assert isbirligi_tamamlandi_mi(adimlar) is beklenen


BUGUN = dt.date(2026, 9, 30)


@pytest.mark.parametrize(
    "hedef,tamamlandi,beklenen",
    [
        (BUGUN - dt.timedelta(days=1), False, True),
        (BUGUN, False, False),  # bugün son gün: henüz gecikmedi
        (BUGUN + dt.timedelta(days=3), False, False),
        (BUGUN - dt.timedelta(days=5), True, False),  # tamamlanan gecikmiş sayılmaz
        (None, False, False),
    ],
)
def test_gecikme_okuma_aninda(hedef, tamamlandi, beklenen):
    assert gecikmis_mi(hedef, tamamlandi, BUGUN) is beklenen
