"""Canlılık kuralları — docs/faz-d-canlilik.md § 1-3'teki tablolar, birebir."""

import datetime as dt

import pytest

from app.agents.canlilik_kurallari import (
    ADIM_GECIKTI,
    ESIKLER,
    GENC_ILGISI_YANITSIZ,
    ILGI_YANITSIZ_1,
    ILGI_YANITSIZ_2,
    ISBIRLIGI_HAREKETSIZ,
    ONERI_BEKLIYOR,
    PLAN_ONAYSIZ,
    YENI_FIRSAT,
    AdimBilgisi,
    Hatirlatma,
    eslesme_hatirlatmalari,
    firsat_mi,
    gecen_gun,
    gecikme_gunu,
    isbirligi_hatirlatmalari,
    tekrar_mi,
)

SIMDI = dt.datetime(2026, 10, 10, 12, 0, tzinfo=dt.UTC)
BUGUN = SIMDI.date()


def test_esikler_onayli_tablo():
    assert ESIKLER == {
        ONERI_BEKLIYOR: 7,
        ILGI_YANITSIZ_1: 3,
        ILGI_YANITSIZ_2: 10,
        PLAN_ONAYSIZ: 5,
        ISBIRLIGI_HAREKETSIZ: 14,
        ADIM_GECIKTI: 1,
        GENC_ILGISI_YANITSIZ: 5,  # genç akışı, plan § 0 karar 6
    }


def test_gecen_gun_asagi_yuvarlar():
    assert gecen_gun(SIMDI - dt.timedelta(days=2, hours=23), SIMDI) == 2
    assert gecen_gun(SIMDI + dt.timedelta(hours=1), SIMDI) == 0  # gelecek: 0


# --- Eşleşme ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "durum,gun,beklenen",
    [
        ("onerildi", 6, []),
        ("onerildi", 7, [Hatirlatma(ONERI_BEKLIYOR, "kurum")]),
        ("ilgileniliyor", 2, []),
        ("ilgileniliyor", 3, [Hatirlatma(ILGI_YANITSIZ_1, "genc")]),
        ("ilgileniliyor", 9, [Hatirlatma(ILGI_YANITSIZ_1, "genc")]),
        (
            "ilgileniliyor",
            10,
            [Hatirlatma(ILGI_YANITSIZ_2, "genc"), Hatirlatma(ILGI_YANITSIZ_2, "kurum")],
        ),
        # Genç ilgi gösterdi, firma yanıtsız: firmaya tek kademe (genç akışı).
        ("genc_ilgilendi", 4, []),
        ("genc_ilgilendi", 5, [Hatirlatma(GENC_ILGISI_YANITSIZ, "kurum")]),
        ("genc_ilgilendi", 30, [Hatirlatma(GENC_ILGISI_YANITSIZ, "kurum")]),
        ("kapandi", 99, []),
        ("kabul_edildi", 99, []),
        ("reddedildi", 99, []),  # kapsam dışı
    ],
)
def test_eslesme_tablosu(durum, gun, beklenen):
    assert eslesme_hatirlatmalari(durum, gun) == beklenen


# --- İş birliği ------------------------------------------------------------------------------


def _adim(id_, gecikme_gunu_, genc=False, kurum=False):
    hedef = BUGUN - dt.timedelta(days=gecikme_gunu_) if gecikme_gunu_ is not None else None
    return AdimBilgisi(id=id_, hedef_tarih=hedef, genc_isaretledi=genc, kurum_isaretledi=kurum)


def _isb(durum="aktif", gun=0, genc_onay=True, kurum_onay=True, adimlar=()):
    return isbirligi_hatirlatmalari(
        durum=durum,
        hareketsiz_gun=gun,
        genc_plan_onayi=genc_onay,
        kurum_plan_onayi=kurum_onay,
        adimlar=list(adimlar),
        bugun=BUGUN,
    )


@pytest.mark.parametrize(
    "genc_onay,kurum_onay,alicilar",
    [(False, False, ["genc", "kurum"]), (True, False, ["kurum"]), (False, True, ["genc"])],
)
def test_plan_onaysiz_yalnizca_onaylamayana(genc_onay, kurum_onay, alicilar):
    sonuc = _isb("plan_bekliyor", 5, genc_onay, kurum_onay)
    assert sonuc == [Hatirlatma(PLAN_ONAYSIZ, rol) for rol in alicilar]
    assert _isb("plan_bekliyor", 4, genc_onay, kurum_onay) == []


def test_hareketsiz_aktif_isbirligi_iki_tarafa():
    assert _isb(gun=13) == []
    assert _isb(gun=14) == [
        Hatirlatma(ISBIRLIGI_HAREKETSIZ, "genc"),
        Hatirlatma(ISBIRLIGI_HAREKETSIZ, "kurum"),
    ]


def test_gecikmis_adim_isaretlememis_tarafa():
    adimlar = [
        _adim("a", 0),  # hedef bugün: henüz gecikmedi
        _adim("b", 1),  # 1 gün geçti: iki tarafa
        _adim("c", 5, genc=True),  # genç işaretledi: yalnız kuruma
        _adim("d", 9, genc=True, kurum=True),  # tamamlandı: yok
        _adim("e", None),  # tarihsiz: yok
    ]
    assert _isb(adimlar=adimlar) == [
        Hatirlatma(ADIM_GECIKTI, "genc", "b"),
        Hatirlatma(ADIM_GECIKTI, "kurum", "b"),
        Hatirlatma(ADIM_GECIKTI, "kurum", "c"),
    ]


def test_gecikme_hareketsizlikten_once_gelir():
    """Gecikme hatırlatması alan kişiye aynı taramada 'hareket yok' gitmez."""
    sonuc = _isb(gun=20, adimlar=[_adim("c", 5, genc=True)])
    assert sonuc == [
        Hatirlatma(ADIM_GECIKTI, "kurum", "c"),
        Hatirlatma(ISBIRLIGI_HAREKETSIZ, "genc"),  # genç gecikmeden haberdar değil
    ]


def test_tamamlanan_isbirligi_hatirlatilmaz():
    assert _isb("tamamlandi", 99, adimlar=[_adim("x", 9)]) == []


def test_gecikme_gunu():
    assert gecikme_gunu(BUGUN - dt.timedelta(days=3), False, BUGUN) == 3
    assert gecikme_gunu(BUGUN - dt.timedelta(days=3), True, BUGUN) == 0
    assert gecikme_gunu(BUGUN + dt.timedelta(days=3), False, BUGUN) == 0
    assert gecikme_gunu(None, False, BUGUN) == 0


# --- Yeni fırsat -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ihtiyac_gun,kart_gun,beklenen",
    [
        (0, 14, True),
        (6, 30, True),
        (7, 30, False),  # ihtiyaç artık yeni değil
        (0, 13, False),  # kart eski değil (genç yeni kartıyla zaten haberdar)
    ],
)
def test_firsat_kosulu(ihtiyac_gun, kart_gun, beklenen):
    assert (
        firsat_mi(
            SIMDI - dt.timedelta(days=ihtiyac_gun), SIMDI - dt.timedelta(days=kart_gun), SIMDI
        )
        is beklenen
    )


# --- Tekrar kuralı ---------------------------------------------------------------------------

HAREKET = SIMDI - dt.timedelta(days=8)


@pytest.mark.parametrize(
    "son_olay,son_aktivite,beklenen",
    [
        (None, HAREKET, False),  # hiç hatırlatılmadı
        (HAREKET + dt.timedelta(days=7), HAREKET, True),  # bu dönemde hatırlatıldı
        (HAREKET - dt.timedelta(days=1), HAREKET, False),  # önceki dönemde; biri hareket etti
    ],
)
def test_tekrar_kurali_donem_basina_bir(son_olay, son_aktivite, beklenen):
    assert tekrar_mi(ONERI_BEKLIYOR, son_olay, son_aktivite) is beklenen


def test_yeni_firsat_bir_kez():
    eski = SIMDI - dt.timedelta(days=30)
    assert tekrar_mi(YENI_FIRSAT, eski, SIMDI) is True  # hareket olsa da bir kez
    assert tekrar_mi(YENI_FIRSAT, None, SIMDI) is False
