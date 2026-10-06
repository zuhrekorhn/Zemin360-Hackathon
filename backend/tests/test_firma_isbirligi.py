"""Firma–firma iş birliği ve takip (docs/plans/firma-akisi.md § 9).

İş birliği ve takip aynı: aday firma, takip kurallarında aday tarafıdır
(`genc_plan_onayi`, `genc_isaret`; karar 12). Plan önerisinin istemi ayrı,
kuralları aynı. Tamamlanan iş birliği aday firmanın bonusuna girer.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select

from app.agents import takip
from app.agents.eslestirme import firma_tamamlanan_isbirligi_sayilari
from app.models.isbirligi import Isbirligi
from tests.takip_dunyasi import sahte_plan
from tests.test_firma_eslestirme import gerekce_sahte as gerekce_sahte  # noqa: F401
from tests.test_firma_ilgi import ONAY, _kurulum
from tests.test_sahiplik import durumlar, senaryo


async def _karsilikli(istemci, d):
    aday, ilan, eid = await _kurulum(d)
    await istemci.post(f"/eslestirme/{eid}/firma-ilgi", headers=aday.baslik, json=ONAY)
    yanit = await istemci.post(
        "/eslestirme/ilgileniyorum", headers=d.kurum1.baslik, json={"eslesme_id": str(eid)}
    )
    return aday, ilan, eid, yanit.json()["isbirligi_id"]


# --- Saf ---------------------------------------------------------------------------------


def test_ozet_girdisi_aday_etiketi():
    girdi = takip.ozet_girdisi(
        durum="aktif",
        genc_adi="Aday Firma",
        kurum_adi="Koop Bir",
        adimlar=[],
        son_hareket=None,
        bugun=dt.date(2026, 9, 30),
        aday_etiketi="ortak firma",
    )
    assert girdi.startswith("Taraflar: ortak firma Aday Firma, kurum Koop Bir.")


def test_istem_adimlari_uydurmaz_pilot_kelimesini_yasaklar():
    assert "SABİT adımları" in takip.SISTEM_TALIMATI
    assert '"Pilot" kelimesini kullanma' in takip.SISTEM_TALIMATI


# --- Gerçek veritabanı -------------------------------------------------------------------


def test_detay_ve_liste_iki_firmaya_acik():
    async def adimlar(istemci, d):
        aday, ilan, eid, isb = await _karsilikli(istemci, d)
        await durumlar(
            istemci,
            "GET",
            f"/isbirligi/{isb}",
            {None: 401, aday: 200, d.kurum1: 200, d.kurum2: 404, d.genc1: 404, d.girvak: 200},
        )
        detay = (await istemci.get(f"/isbirligi/{isb}", headers=aday.baslik)).json()
        assert detay["aday_turu"] == "firma"
        assert detay["aday_adi"] == "Aday Firma"
        assert detay["genc_adi"] is None and detay["yetenek_karti_id"] is None
        assert detay["iletisim"]["kurum_email"] == d.kurum1.profil.iletisim_email
        # Taraf rolden değil eşleşmeden: ortak firmanın rolü de "kurum".
        assert detay["tarafim"] == "genc"
        ilan_tarafi = (await istemci.get(f"/isbirligi/{isb}", headers=d.kurum1.baslik)).json()
        assert ilan_tarafi["tarafim"] == "kurum"
        girvak = (await istemci.get(f"/isbirligi/{isb}", headers=d.girvak.baslik)).json()
        assert girvak["tarafim"] is None

        for kisi in (aday, d.kurum1):
            liste = (await istemci.get("/isbirliklerim", headers=kisi.baslik)).json()
            satir = next(s for s in liste if s["isbirligi_id"] == isb)
            assert satir["aday_adi"] == "Aday Firma"
            assert satir["aday_turu"] == "firma"
            assert satir["tarafim"] == ("genc" if kisi is aday else "kurum")
        baskasi = (await istemci.get("/isbirliklerim", headers=d.kurum2.baslik)).json()
        assert all(s["isbirligi_id"] != isb for s in baskasi)

    senaryo(adimlar)


def test_plan_onerisi_firma_istemini_kullanir(monkeypatch):
    cagrilar = sahte_plan(monkeypatch, sonuc=RuntimeError("model yok"))

    async def adimlar(istemci, d):
        aday, ilan, eid, isb = await _karsilikli(istemci, d)
        yanit = await istemci.post(f"/isbirligi/{isb}/plan-oner", headers=aday.baslik)
        assert yanit.status_code == 200
        govde = yanit.json()
        # Firma ilanı: firma–firma şablonlarından biri, model hatasında şablon metniyle dolu.
        assert govde["surec"] in ("pilot", "tedarik", "isbirligi")
        assert len(govde["milestonelar"]) == 5
        assert cagrilar[0]["aday_basligi"] == "ORTAK FİRMA (Aday Firma)"
        assert cagrilar[0]["kurum_adi"] == "Koop Bir"
        assert "Müsaitlik" not in cagrilar[0]["ilan"]

    senaryo(adimlar)


def test_iki_firma_plani_onaylar_tamamlar_bonusa_girer():
    async def adimlar(istemci, d):
        aday, ilan, eid, isb = await _karsilikli(istemci, d)
        ekle = await istemci.post(
            f"/isbirligi/{isb}/milestone-ekle",
            headers=aday.baslik,
            json={"baslik": "Pilot depo", "hedef_tarih": "2026-10-30"},
        )
        assert ekle.status_code == 201
        adim_id = ekle.json()["milestonelar"][0]["id"]

        for kisi in (aday, d.kurum1):
            onay = await istemci.post(f"/isbirligi/{isb}/plan-onayla", headers=kisi.baslik)
            assert onay.status_code == 200
        assert onay.json()["durum"] == "aktif"

        for kisi in (aday, d.kurum1):
            isaret = await istemci.post(
                f"/isbirligi/{isb}/milestone/{adim_id}/isaretle", headers=kisi.baslik
            )
            assert isaret.status_code == 200
        assert isaret.json()["durum"] == "tamamlandi"

        isbirligi = await d.oturum.scalar(
            select(Isbirligi)
            .where(Isbirligi.eslesme_id == eid)
            .execution_options(populate_existing=True)
        )
        assert isbirligi.durum == "tamamlandi"
        sayilar = await firma_tamamlanan_isbirligi_sayilari(d.oturum, [aday.kart.id])
        assert sayilar == {aday.kart.id: 1}

    senaryo(adimlar)


def test_girvak_kirilimi_turleri_ayri_sayar():
    """Toplamlar iki türü birlikte sayar; kırılım ayrı (firma-akisi § 0 karar 19).

    Sayılar bütün veritabanını sayıyor (yerelde başka kayıtlar olabilir): fark ölçülür.
    """

    async def adimlar(istemci, d):
        async def sayilar():
            return (await istemci.get("/girvak/sayilar", headers=d.girvak.baslik)).json()

        once = await sayilar()
        await _karsilikli(istemci, d)
        sonra = await sayilar()

        def fark(tur, alan):
            return sonra["kirilim"][tur][alan] - once["kirilim"][tur][alan]

        assert fark("firma_firma", "karsilikli_ilgi") == 1
        assert fark("firma_firma", "isbirligi") == 1
        assert fark("genc_firma", "karsilikli_ilgi") == 0
        assert fark("genc_firma", "isbirligi") == 0
        # Toplam firma–firma'yı da sayar.
        assert sonra["eslesme"]["kabul_edildi"] - once["eslesme"]["kabul_edildi"] == 1

    senaryo(adimlar)
