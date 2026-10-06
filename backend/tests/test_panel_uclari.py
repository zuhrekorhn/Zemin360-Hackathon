"""Panellerin okuduğu uçlar (docs/faz-b-kimlik-ve-dongu.md § 7), gerçek veritabanında.

Dünya test_sahiplik.py'deki: E1 = I1 (kurum1) ↔ K1 (genc1, "Elif"), `onerildi`;
E2 = I2 (kurum2) ↔ K2 (genc2, "Can"), `ilgileniliyor`.
"""

import datetime as dt

from app.models.eslesme import Eslesme
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.somut_cikti import SomutCikti
from tests.test_sahiplik import durumlar, senaryo


async def _ikinci_ihtiyac(d):
    """kurum1'e I1'den SONRA açılmış ikinci kart; K2 ona önerilmiş."""
    d.I1b = IhtiyacKarti(
        kurum_id=d.kurum1.profil.id,
        problem_tanimi="Raporlar elle hazırlanıyor",
        olusturma_tarihi=dt.datetime.now(dt.UTC) + dt.timedelta(minutes=1),
    )
    d.oturum.add(d.I1b)
    await d.oturum.flush()
    d.E1b = Eslesme(
        ihtiyac_karti_id=d.I1b.id, yetenek_karti_id=d.K2.id, skor=0.55, durum="onerildi"
    )
    d.oturum.add(d.E1b)
    await d.oturum.commit()


def test_oneriler_istenen_ihtiyac_kartina_gore():
    async def adimlar(istemci, d):
        await _ikinci_ihtiyac(d)
        yol = f"/eslestirme/oneriler/{d.kurum1.profil.id}"

        varsayilan = (await istemci.get(yol, headers=d.kurum1.baslik)).json()
        assert varsayilan["ihtiyac_karti_id"] == str(d.I1b.id)  # en son kart

        istenen = await istemci.get(
            yol, params={"ihtiyac_karti_id": str(d.I1.id)}, headers=d.kurum1.baslik
        )
        assert istenen.status_code == 200
        assert [o["eslesme_id"] for o in istenen.json()["oneriler"]] == [str(d.E1.id)]

        # Başka kurumun kartı: 404 (varlığı sızmasın).
        baskasinin = await istemci.get(
            yol, params={"ihtiyac_karti_id": str(d.I2.id)}, headers=d.kurum1.baslik
        )
        assert baskasinin.status_code == 404

    senaryo(adimlar)


def test_onerilerim_tum_kartlardan_gencin_adiyla_epostasiz():
    async def adimlar(istemci, d):
        await _ikinci_ihtiyac(d)
        yanit = await istemci.get("/eslestirme/onerilerim", headers=d.kurum1.baslik)
        assert yanit.status_code == 200
        satirlar = yanit.json()
        assert {s["eslesme_id"] for s in satirlar} == {str(d.E1.id), str(d.E1b.id)}
        adlar = {s["eslesme_id"]: s["genc_adi"] for s in satirlar}
        assert adlar[str(d.E1.id)] == "Elif"
        assert adlar[str(d.E1b.id)] == "Can"
        assert all(s["iletisim"] is None for s in satirlar)
        for kisi in (d.genc1, d.genc2):
            assert kisi.hesap.email not in yanit.text

        await durumlar(
            istemci,
            "GET",
            "/eslestirme/onerilerim",
            {None: 401, d.genc1: 403, d.girvak: 403, d.kurum2: 200},
        )
        # kurum2 yalnızca kendininkini görür.
        kurum2 = (await istemci.get("/eslestirme/onerilerim", headers=d.kurum2.baslik)).json()
        assert [s["eslesme_id"] for s in kurum2] == [str(d.E2.id)]

    senaryo(adimlar)


def test_eposta_taslagi_alanlari_uc_yanitta_ve_adres_sizmaz():
    """E-posta taslağı için başarı ölçütü ve çalışma başlığı gelir; adres yalnızca `iletisim`'de."""

    async def adimlar(istemci, d):
        d.I1.basari_kriteri = "Raporlar günde bir kez otomatik çıkmalı"
        d.oturum.add(
            SomutCikti(yetenek_karti_id=d.K1.id, baslik="Eski panel", tarih=dt.date(2023, 1, 1))
        )
        d.oturum.add(
            SomutCikti(yetenek_karti_id=d.K1.id, baslik="Sensör paneli", tarih=dt.date(2025, 6, 1))
        )
        await d.oturum.commit()

        await istemci.post(
            "/eslestirme/ilgileniyorum",
            headers=d.kurum1.baslik,
            json={"eslesme_id": str(d.E1.id)},
        )
        kabul = await istemci.post(f"/eslestirme/{d.E1.id}/kabul", headers=d.genc1.baslik)
        isbirligi_id = kabul.json()["isbirligi_id"]

        oneri = next(
            s
            for s in (await istemci.get("/eslestirme/onerilerim", headers=d.kurum1.baslik)).json()
            if s["eslesme_id"] == str(d.E1.id)
        )
        assert oneri["basari_kriteri"] == "Raporlar günde bir kez otomatik çıkmalı"
        assert oneri["calisma_basligi"] == "Sensör paneli"  # en yeni tarihli

        for taraf in (d.genc1, d.kurum1):
            ozet = next(
                s
                for s in (await istemci.get("/isbirliklerim", headers=taraf.baslik)).json()
                if s["isbirligi_id"] == isbirligi_id
            )
            assert ozet["calisma_basligi"] == "Sensör paneli"
            assert ozet["basari_kriteri"] == "Raporlar günde bir kez otomatik çıkmalı"

        detay = await istemci.get(f"/isbirligi/{isbirligi_id}", headers=d.genc1.baslik)
        assert detay.json()["calisma_basligi"] == "Sensör paneli"

        # GİRVAK: iletişim null; yeni alanlar adres taşımaz.
        girvak = await istemci.get(f"/isbirligi/{isbirligi_id}", headers=d.girvak.baslik)
        assert girvak.json()["iletisim"] is None
        for kisi in (d.genc1, d.kurum1):
            assert kisi.hesap.email not in girvak.text

        # Kabul öncesi eşleşmede (kurum2'nin E2'si) adres yok.
        oncesi = await istemci.get("/eslestirme/onerilerim", headers=d.kurum2.baslik)
        assert all(s["iletisim"] is None for s in oncesi.json())

    senaryo(adimlar)


def test_girvak_sayilari():
    async def adimlar(istemci, d):
        await durumlar(
            istemci,
            "GET",
            "/girvak/sayilar",
            {None: 401, d.genc1: 403, d.kurum1: 403, d.girvak: 200},
        )
        once = (await istemci.get("/girvak/sayilar", headers=d.girvak.baslik)).json()
        assert once["hesap"]["genc"] >= 2
        assert once["eslesme"]["onerildi"] >= 1

        await istemci.post(
            "/eslestirme/ilgileniyorum",
            headers=d.kurum1.baslik,
            json={"eslesme_id": str(d.E1.id)},
        )
        await istemci.post(f"/eslestirme/{d.E1.id}/kabul", headers=d.genc1.baslik)
        sonra = (await istemci.get("/girvak/sayilar", headers=d.girvak.baslik)).json()
        assert sonra["eslesme"]["kabul_edildi"] == once["eslesme"]["kabul_edildi"] + 1
        assert sonra["eslesme"]["onerildi"] == once["eslesme"]["onerildi"] - 1
        assert sonra["isbirligi"] == once["isbirligi"] + 1
        # Yalnızca sayı: hiçbir e-posta ya da ad yok.
        assert "@" not in str(sonra) and "Elif" not in str(sonra)

    senaryo(adimlar)
