"""Firmalar arası ilgi (docs/plans/firma-akisi.md § 0 karar 8, § 3, § 10).

Aynı durum makinesi: aday firma makinenin aday tarafının geçişlerini yapar.
İki yönlü: ilan sahibi ilk ilgiyi gösterebilir (aday kabul/ret eder) ya da
aday firma gösterebilir (ilan sahibi karşılıklı ilgi / şimdilik değil).
"""

from __future__ import annotations

from sqlalchemy import select

from app.models.bildirim import (
    TUR_FIRSAT_KAPANDI,
    TUR_GENC_ILGI,
    TUR_ILGI,
    TUR_KABUL,
    TUR_KARSILIKLI_ILGI,
    TUR_RED,
    Bildirim,
)
from app.models.eslesme import Eslesme
from app.models.isbirligi import Isbirligi
from app.servisler import eslestirme as servis
from tests.test_firma_eslestirme import _firma, _ortak_ilan
from tests.test_firma_eslestirme import gerekce_sahte as gerekce_sahte  # noqa: F401
from tests.test_sahiplik import durumlar, senaryo

ONAY = {"iletisim_onayi": True}


async def _kurulum(d):
    """Aday firma + ortak ilanı + önerilmiş eşleşme."""
    aday = await _firma(d, "Aday Firma")
    ilan = await _ortak_ilan(d)
    await servis.pipeline_calistir(d.oturum, ilan)
    eslesme_id = await d.oturum.scalar(
        select(Eslesme.id).where(Eslesme.ihtiyac_karti_id == ilan.id)
    )
    return aday, ilan, eslesme_id


async def _eslesme(d, eslesme_id) -> Eslesme:
    return await d.oturum.scalar(
        select(Eslesme).where(Eslesme.id == eslesme_id).execution_options(populate_existing=True)
    )


async def _bildirimler(d, hesap_id, tur) -> list[str]:
    return list(
        await d.oturum.scalars(
            select(Bildirim.metin).where(Bildirim.hesap_id == hesap_id, Bildirim.tur == tur)
        )
    )


def test_aday_firma_ilgi_gosterir_ilan_sahibi_karsilik_verir():
    async def adimlar(istemci, d):
        aday, ilan, eid = await _kurulum(d)

        ilgi = await istemci.post(f"/eslestirme/{eid}/firma-ilgi", headers=aday.baslik, json=ONAY)
        assert ilgi.status_code == 200
        assert ilgi.json()["durum"] == "genc_ilgilendi"
        assert ilgi.json()["iletisim"] is None
        metinler = await _bildirimler(d, d.kurum1.hesap.id, TUR_GENC_ILGI)
        assert metinler == [
            "Aday Firma iş birliği ilanınızla ilgileniyor. Siz de ilgilenirseniz iletişim "
            "bilgileriniz karşılıklı paylaşılır."
        ]

        # Tekrar: 200, ikinci bildirim yok.
        tekrar = await istemci.post(f"/eslestirme/{eid}/firma-ilgi", headers=aday.baslik, json=ONAY)
        assert tekrar.status_code == 200
        assert len(await _bildirimler(d, d.kurum1.hesap.id, TUR_GENC_ILGI)) == 1

        karsilik = await istemci.post(
            "/eslestirme/ilgileniyorum", headers=d.kurum1.baslik, json={"eslesme_id": str(eid)}
        )
        assert karsilik.status_code == 200
        govde = karsilik.json()
        assert govde["durum"] == "kabul_edildi"
        assert govde["isbirligi_id"] is not None
        assert govde["iletisim"]["aday_firma_email"] == aday.profil.iletisim_email
        assert govde["iletisim"]["genc_email"] is None
        assert (await _bildirimler(d, aday.hesap.id, TUR_KARSILIKLI_ILGI)) == [
            "Koop Bir ilginize karşılık verdi. İletişim bilgileriniz paylaşıldı ve iş "
            "birliği başladı."
        ]

        # Aday firma da iletişimi görür; başka firma eşleşmeyi hiç görmez.
        liste = (await istemci.get("/eslestirme/firma-eslesmelerim", headers=aday.baslik)).json()
        assert liste[0]["durum"] == "kabul_edildi"
        assert liste[0]["iletisim"]["kurum_email"] == d.kurum1.profil.iletisim_email
        baskasi = await istemci.get("/eslestirme/firma-eslesmelerim", headers=d.kurum2.baslik)
        assert baskasi.json() == []

    senaryo(adimlar)


def test_ilan_sahibi_once_ilgilenir_aday_kabul_ya_da_ret(plan_arka_plan_isi_yok):
    async def adimlar(istemci, d):
        aday, ilan, eid = await _kurulum(d)
        ilgi = await istemci.post(
            "/eslestirme/ilgileniyorum", headers=d.kurum1.baslik, json={"eslesme_id": str(eid)}
        )
        assert ilgi.json()["durum"] == "ilgileniliyor"
        assert (await _bildirimler(d, aday.hesap.id, TUR_ILGI)) == [
            "Koop Bir, iş birliği ilanı için firmanızla ilgileniyor. Kabul ederseniz "
            "e-posta adresleriniz paylaşılır."
        ]

        kabul = await istemci.post(f"/eslestirme/{eid}/firma-kabul", headers=aday.baslik)
        assert kabul.status_code == 200
        assert kabul.json()["durum"] == "kabul_edildi"
        isbirligi = await d.oturum.scalar(select(Isbirligi).where(Isbirligi.eslesme_id == eid))
        assert isbirligi is not None
        assert plan_arka_plan_isi_yok == [isbirligi.id]
        assert (await _bildirimler(d, d.kurum1.hesap.id, TUR_KABUL)) == [
            "Aday Firma ilginizi kabul etti; iletişim bilgileri açıldı."
        ]

        # Kabul edilmiş eşleşmede ret geçersiz geçiş: 409.
        red = await istemci.post(f"/eslestirme/{eid}/firma-red", headers=aday.baslik)
        assert red.status_code == 409

    senaryo(adimlar)


def test_aday_firma_reddeder_ve_geri_ceker():
    async def adimlar(istemci, d):
        aday, ilan, eid = await _kurulum(d)
        await istemci.post(f"/eslestirme/{eid}/firma-ilgi", headers=aday.baslik, json=ONAY)
        geri = await istemci.post(f"/eslestirme/{eid}/firma-ilgiyi-geri-cek", headers=aday.baslik)
        assert geri.json()["durum"] == "onerildi"
        eslesme = await _eslesme(d, eid)
        assert eslesme.baslatan is None and eslesme.genc_iletisim_onayi_tarihi is None

        await istemci.post(
            "/eslestirme/ilgileniyorum", headers=d.kurum1.baslik, json={"eslesme_id": str(eid)}
        )
        red = await istemci.post(f"/eslestirme/{eid}/firma-red", headers=aday.baslik)
        assert red.json()["durum"] == "reddedildi"
        assert (await _bildirimler(d, d.kurum1.hesap.id, TUR_RED)) == [
            "Aday Firma bu eşleşmeyi şu an kabul etmedi."
        ]

    senaryo(adimlar)


def test_simdilik_degil_aday_firmaya_notr_bildirim():
    async def adimlar(istemci, d):
        aday, ilan, eid = await _kurulum(d)
        await istemci.post(f"/eslestirme/{eid}/firma-ilgi", headers=aday.baslik, json=ONAY)
        yanit = await istemci.post(f"/eslestirme/{eid}/simdilik-degil", headers=d.kurum1.baslik)
        assert yanit.json()["durum"] == "kapandi"
        assert (await _bildirimler(d, aday.hesap.id, TUR_FIRSAT_KAPANDI)) == [
            "Koop Bir tarafındaki fırsat kapandı."
        ]

    senaryo(adimlar)


def test_yetki_ve_kurallar():
    async def adimlar(istemci, d):
        aday, ilan, eid = await _kurulum(d)
        yol = f"/eslestirme/{eid}/firma-ilgi"
        # 401 token yok, 403 genç/GİRVAK, 404 taraf olmayan firma ve ilan sahibi (aday değil).
        await durumlar(
            istemci,
            "POST",
            yol,
            {None: 401, d.genc1: 403, d.girvak: 403, d.kurum2: 404, d.kurum1: 404},
            json=ONAY,
        )
        # Açık onay zorunlu.
        onaysiz = await istemci.post(yol, headers=aday.baslik, json={})
        assert onaysiz.status_code == 422
        # Aday firma genç uçlarını kullanamaz (rol), genç eşleşmesi firma uçlarında yok.
        genc_ucu = await istemci.post(
            f"/eslestirme/{eid}/genc-ilgi", headers=aday.baslik, json=ONAY
        )
        assert genc_ucu.status_code == 403
        genc_eslesmesi = await istemci.post(
            f"/eslestirme/{d.E1.id}/firma-ilgi", headers=d.kurum1.baslik, json=ONAY
        )
        assert genc_eslesmesi.status_code == 404

        # Eşik altı öneriye ilgi gösterilemez.
        eslesme = await _eslesme(d, eid)
        eslesme.skor = 0.1
        await d.oturum.commit()
        esik_alti = await istemci.post(yol, headers=aday.baslik, json=ONAY)
        assert esik_alti.status_code == 409

    senaryo(adimlar)


def test_aday_firma_ilani_gorur_baskasi_gormez():
    async def adimlar(istemci, d):
        aday, ilan, eid = await _kurulum(d)
        await durumlar(
            istemci,
            "GET",
            f"/ihtiyac-kartlari/{ilan.id}",
            {aday: 200, d.kurum1: 200, d.kurum2: 404, d.genc1: 404, d.girvak: 200},
        )

    senaryo(adimlar)
