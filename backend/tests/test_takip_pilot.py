"""Tamamlanmış pilot sinyali (docs/takip.md § 6).

Geri besleme döngüsü: iş birliği tamamlanınca gencin kartında sinyal görünür
ve Eşleştirme'nin doğrulama bonusuna girer. Karar: toplamsal, tavanlı formül —
pilotu olmayan kartın skoru değişmez, pilot en çok +0.125 ekler, alakayı yaratmaz.
"""

import datetime as dt
from types import SimpleNamespace

import pytest

from app.agents.eslestirme import (
    BENZERLIK_ALT_SINIRI,
    PILOT_BONUSU,
    Aday,
    adaylari_getir,
    dogrulama_bonusu,
    gerekce_girdileri,
    siralayip_ele,
    skor_hesapla,
)
from app.db.base import EMBEDDING_DIM
from app.models.ihtiyac_karti import IhtiyacKarti
from scripts import demo_hesaplari
from tests.test_sahiplik import senaryo
from tests.test_takip_isaret import aktif_isbirligi

# --- Formül (saf) --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "guven,pilot,beklenen",
    [
        ([], 0, 0.0),
        ([], 1, 0.5),
        ([], 3, 0.5),  # sayı değil varlık: bir pilot yeter
        ([(3, 3, 0, 0)], 0, 0.5),
        ([(3, 3, 0, 0)], 1, 1.0),
        ([(3, 3, 3, 3)], 1, 1.0),  # tavan
        ([(3, 3, 3, 0), (0, 0, 0, 0)], 1, 0.875),
    ],
)
def test_bonus_formulu(guven, pilot, beklenen):
    assert dogrulama_bonusu(guven, tamamlanan_pilot=pilot) == pytest.approx(beklenen)


@pytest.mark.parametrize(
    "guven", [[], [(1, 2, 3, 0)], [(3, 3, 3, 3)], [(2, 2, 2, 2), (0, 1, 0, 0)]]
)
def test_pilotsuz_kartin_bonusu_faz_c_oncesiyle_ayni(guven):
    oncesi = 0.0 if not guven else sum(sum(g) / 12 for g in guven) / len(guven)
    assert dogrulama_bonusu(guven) == pytest.approx(oncesi)
    assert dogrulama_bonusu(guven, tamamlanan_pilot=0) == pytest.approx(oncesi)


@pytest.mark.parametrize("guven", [[], [(1, 1, 1, 0)], [(3, 3, 3, 3)]])
def test_pilot_skora_en_cok_0125_ekler(guven):
    benzerlik = 0.6
    fark = skor_hesapla(benzerlik, dogrulama_bonusu(guven, 1)) - skor_hesapla(
        benzerlik, dogrulama_bonusu(guven)
    )
    assert 0 <= fark <= 0.25 * PILOT_BONUSU + 1e-9


def test_demo_kalibrasyonu_bozulmadi():
    """Kanıtsız, pilotsuz demo kartı: benzerlik 0.589, tabanın (0.48) üstünde."""
    assert "görecek" in demo_hesaplari.oneri_durumu(0.589)


def test_pilot_alakayi_yaratmaz():
    """Tam doğrulanmış ve pilotlu ama konu dışı aday, alt sınırda elenir."""
    kart = SimpleNamespace(id="k")
    alakasiz = Aday(
        yetenek_karti=kart,
        benzerlik=BENZERLIK_ALT_SINIRI - 0.01,
        dogrulama_bonus=dogrulama_bonusu([(3, 3, 3, 3)], 1),
        tamamlanan_pilot=1,
    )
    assert alakasiz.skor > skor_hesapla(BENZERLIK_ALT_SINIRI, 0.0)  # skoru tabandakinden yüksek…
    assert siralayip_ele([alakasiz]) == []  # …ama alaka elemesi skordan önce


def test_gerekce_istemi_pilotu_soyler():
    ihtiyac = SimpleNamespace(problem_tanimi="p", basari_kriteri=None, kisitlar=None)
    kart = SimpleNamespace(
        rol_alani="r",
        deneyim_seviyesi="orta",
        sektor_ilgi_alani=[],
        araclar_teknolojiler=[],
        somut_ciktilar=[],
    )
    assert "Tamamlanmış pilot: yok." in gerekce_girdileri(ihtiyac, kart)["dogrulama"]
    pilotlu = gerekce_girdileri(ihtiyac, kart, tamamlanan_pilot=1)["dogrulama"]
    assert "Tamamlanmış pilot: 1" in pilotlu


# --- Döngü kapanıyor (gerçek veritabanında) -------------------------------------------------


def test_tamamlanan_isbirligi_kart_gorunumune_ve_eslestirmeye_girer():
    async def adimlar(istemci, d):
        vektor = [0.0] * EMBEDDING_DIM
        vektor[11] = 1.0
        d.K1.embedding = vektor
        d.K2.embedding = vektor  # aynı alaka, pilotsuz karşılaştırma kartı
        await d.oturum.commit()

        isb = await aktif_isbirligi(d, adimlar=1)
        adim = isb.milestonelar[0]
        kart_yolu = f"/yetenek-kartlari/{d.K1.id}"
        assert (await istemci.get(kart_yolu, headers=d.genc1.baslik)).json()[
            "tamamlanan_pilot"
        ] == 0

        for kisi in (d.genc1, d.kurum1):
            await istemci.post(
                f"/isbirligi/{isb.id}/milestone/{adim.id}/isaretle", headers=kisi.baslik
            )
        assert (await istemci.get(f"/isbirligi/{isb.id}", headers=d.genc1.baslik)).json()[
            "durum"
        ] == "tamamlandi"

        # Kart görünümü: gence de, karta önerilmiş kuruma da.
        for kisi in (d.genc1, d.kurum1):
            yanit = await istemci.get(kart_yolu, headers=kisi.baslik)
            assert yanit.json()["tamamlanan_pilot"] == 1
            assert "Koop" not in yanit.text  # kurum adı taşımaz

        # Eşleştirme: yeni bir ihtiyaçta pilotlu kart bonusu alır, diğeri almaz.
        yeni = IhtiyacKarti(
            kurum_id=d.kurum2.profil.id,
            problem_tanimi="Yeni ihtiyaç",
            embedding=vektor,
            olusturma_tarihi=dt.datetime.now(dt.UTC),
        )
        d.oturum.add(yeni)
        await d.oturum.flush()
        adaylar = {a.yetenek_karti.id: a for a in await adaylari_getir(d.oturum, yeni)}
        assert adaylar[d.K1.id].tamamlanan_pilot == 1
        assert adaylar[d.K1.id].dogrulama_bonus == pytest.approx(PILOT_BONUSU)
        assert adaylar[d.K2.id].tamamlanan_pilot == 0
        assert adaylar[d.K2.id].dogrulama_bonus == 0.0
        assert adaylar[d.K1.id].skor - adaylar[d.K2.id].skor == pytest.approx(0.125)

    senaryo(adimlar)
