"""İki taraflı döngü uçtan uca (docs/faz-b-kimlik-ve-dongu.md § 5), gerçek veritabanında.

Dünya test_sahiplik.py'deki: E1 = I1 (kurum1) ↔ K1 (genc1, "Elif"), `onerildi`;
E2 = I2 (kurum2) ↔ K2 (genc2), `ilgileniliyor`.

Sabitlenenler:
- "İlgileniyorum" iş birliği açmaz; iş birliği gencin kabulüyle açılır.
- Aynı geçişin tekrarı 200, yan etkisiz (tek iş birliği, aktivite tarihi aynı).
- Geçersiz geçiş 409 ve mevcut durumu söyler.
- Kabulden önce hiçbir yanıtta e-posta yok; gencin adı var. Kabulden sonra
  e-postalar `iletisim`'de yalnızca iki tarafa açılır, GİRVAK'a değil.
"""

import datetime as dt

from sqlalchemy import func, select

from app.models.eslesme import Eslesme
from app.models.isbirligi import Isbirligi
from app.models.yetenek_karti import YetenekKarti
from tests.test_sahiplik import _hesap, durumlar, senaryo


def _epostalar(d):
    return {d.genc1.hesap.email, d.kurum1.hesap.email}


async def _aktivite(d, eslesme_id):
    """Uç noktayla aynı oturumdan okunur (api_istemcisi oturumu paylaşıyor)."""
    return await d.oturum.scalar(
        select(Eslesme.son_aktivite_tarihi).where(Eslesme.id == eslesme_id)
    )


async def _isbirligi_sayisi(d, eslesme_id):
    return await d.oturum.scalar(
        select(func.count()).select_from(Isbirligi).where(Isbirligi.eslesme_id == eslesme_id)
    )


def test_kabul_yolu_ve_eposta_gizliligi():
    async def adimlar(istemci, d):
        e1 = str(d.E1.id)
        oneriler_yolu = f"/eslestirme/oneriler/{d.kurum1.profil.id}"

        # Kurum ilgi bildirmeden "bana gelen ilgiler" boş ve kabul edilecek bir şey yok.
        # Genç akışında (plan § 0, karar 1) genç önerilen eşleşmeyi görür: 409, 404 değil.
        assert (await istemci.get("/eslestirme/bana-gelenler", headers=d.genc1.baslik)).json() == []
        yanit = await istemci.post(f"/eslestirme/{e1}/kabul", headers=d.genc1.baslik)
        assert yanit.status_code == 409

        ilgi = await istemci.post(
            "/eslestirme/ilgileniyorum", headers=d.kurum1.baslik, json={"eslesme_id": e1}
        )
        assert ilgi.status_code == 200
        assert ilgi.json()["durum"] == "ilgileniliyor"
        assert ilgi.json()["isbirligi_id"] is None
        assert await _isbirligi_sayisi(d, d.E1.id) == 0

        # Çift tıklama: 200, aynı durum, aktivite tarihi değişmez.
        once = await _aktivite(d, d.E1.id)
        tekrar = await istemci.post(
            "/eslestirme/ilgileniyorum", headers=d.kurum1.baslik, json={"eslesme_id": e1}
        )
        assert tekrar.status_code == 200
        assert tekrar.json()["durum"] == "ilgileniliyor"
        assert await _aktivite(d, d.E1.id) == once

        # Kabulden önce: iki tarafın gördüğü hiçbir yanıtta e-posta yok, ad var.
        kabul_oncesi = [
            ilgi,
            await istemci.get(oneriler_yolu, headers=d.kurum1.baslik),
            await istemci.get(f"/yetenek-kartlari/{d.K1.id}", headers=d.kurum1.baslik),
            await istemci.get("/eslestirme/bana-gelenler", headers=d.genc1.baslik),
            await istemci.get(f"/ihtiyac-kartlari/{d.I1.id}", headers=d.genc1.baslik),
            await istemci.get("/isbirliklerim", headers=d.genc1.baslik),
            await istemci.get("/isbirliklerim", headers=d.kurum1.baslik),
        ]
        for yanit in kabul_oncesi:
            assert yanit.status_code == 200, yanit.request.url
            assert not any(e in yanit.text for e in _epostalar(d)), yanit.request.url
        assert "Elif" in kabul_oncesi[1].text  # öneriler
        assert "Elif" in kabul_oncesi[2].text  # kart sayfası
        gelenler = kabul_oncesi[3].json()
        assert [g["eslesme_id"] for g in gelenler] == [e1]
        assert gelenler[0]["ihtiyac_karti"]["kurum"]["ad"] == "Koop Bir"
        assert gelenler[0]["iletisim"] is None

        # Kabul: iş birliği açılır, e-postalar iki tarafa görünür.
        kabul = await istemci.post(f"/eslestirme/{e1}/kabul", headers=d.genc1.baslik)
        assert kabul.status_code == 200
        govde = kabul.json()
        assert govde["durum"] == "kabul_edildi"
        assert govde["isbirligi_id"] is not None
        assert govde["iletisim"] == {
            "genc_email": d.genc1.hesap.email,
            "kurum_email": d.kurum1.hesap.email,
        }
        assert await _aktivite(d, d.E1.id) > once

        # Kabulün tekrarı ikinci bir iş birliği açmaz.
        yine = await istemci.post(f"/eslestirme/{e1}/kabul", headers=d.genc1.baslik)
        assert yine.status_code == 200
        assert yine.json()["isbirligi_id"] == govde["isbirligi_id"]
        assert await _isbirligi_sayisi(d, d.E1.id) == 1

        # Kabulden sonra red ve yeniden ilgi 409, mevcut durumu söyleyerek.
        red = await istemci.post(f"/eslestirme/{e1}/red", headers=d.genc1.baslik)
        assert red.status_code == 409
        assert "kabul edildi" in red.json()["detail"]

        # Kurum önerilerinde de iletişim açık; GİRVAK aynı listeyi görür ama e-postasız.
        oneri = (await istemci.get(oneriler_yolu, headers=d.kurum1.baslik)).json()
        assert oneri["oneriler"][0]["iletisim"]["genc_email"] == d.genc1.hesap.email
        girvak = await istemci.get(oneriler_yolu, headers=d.girvak.baslik)
        assert girvak.status_code == 200
        assert not any(e in girvak.text for e in _epostalar(d))

        # İş birliklerim: iki tarafa aynı görünüm; üçüncü kişiye yok.
        for kisi in (d.genc1, d.kurum1):
            liste = (await istemci.get("/isbirliklerim", headers=kisi.baslik)).json()
            assert [i["isbirligi_id"] for i in liste] == [govde["isbirligi_id"]]
            assert liste[0]["genc_adi"] == "Elif"
            assert liste[0]["kurum_adi"] == "Koop Bir"
            assert liste[0]["iletisim"]["kurum_email"] == d.kurum1.hesap.email
        for kisi in (d.genc2, d.kurum2):
            assert (await istemci.get("/isbirliklerim", headers=kisi.baslik)).json() == []

    senaryo(adimlar)


def test_red_yolu():
    async def adimlar(istemci, d):
        e2 = str(d.E2.id)
        red = await istemci.post(f"/eslestirme/{e2}/red", headers=d.genc2.baslik)
        assert red.status_code == 200
        assert red.json() == {
            "eslesme_id": e2,
            "durum": "reddedildi",
            "isbirligi_id": None,
            "iletisim": None,
        }
        # Tekrar: 200, yan etkisiz.
        assert (
            await istemci.post(f"/eslestirme/{e2}/red", headers=d.genc2.baslik)
        ).status_code == 200

        kabul = await istemci.post(f"/eslestirme/{e2}/kabul", headers=d.genc2.baslik)
        assert kabul.status_code == 409
        ilgi = await istemci.post(
            "/eslestirme/ilgileniyorum", headers=d.kurum2.baslik, json={"eslesme_id": e2}
        )
        assert ilgi.status_code == 409
        assert "reddedildi" in ilgi.json()["detail"]
        assert await _isbirligi_sayisi(d, d.E2.id) == 0

        # Reddedilen de gencin listesinde kalır (durumuyla).
        gelenler = (await istemci.get("/eslestirme/bana-gelenler", headers=d.genc2.baslik)).json()
        assert [(g["eslesme_id"], g["durum"]) for g in gelenler] == [(e2, "reddedildi")]

    senaryo(adimlar)


def test_kabul_ve_red_yalnizca_kartin_sahibi_genc():
    async def adimlar(istemci, d):
        for eylem in ("kabul", "red"):
            await durumlar(
                istemci,
                "POST",
                f"/eslestirme/{d.E2.id}/{eylem}",
                {None: 401, d.kurum2: 403, d.girvak: 403, d.genc1: 404},
            )

    senaryo(adimlar)


def test_bana_gelenler_ve_isbirliklerim_rolleri():
    async def adimlar(istemci, d):
        await durumlar(
            istemci,
            "GET",
            "/eslestirme/bana-gelenler",
            {None: 401, d.kurum1: 403, d.girvak: 403, d.genc1: 200},
        )
        await durumlar(
            istemci,
            "GET",
            "/isbirliklerim",
            {None: 401, d.girvak: 403, d.genc1: 200, d.kurum1: 200},
        )

    senaryo(adimlar)


def test_isbirliklerim_son_aktiviteye_gore_siralanir():
    """Başlangıç tarihi değil eşleşmenin son hareketi belirler (en yeni önce)."""

    async def adimlar(istemci, d):
        simdi = dt.datetime.now(dt.UTC)
        genc3 = await _hesap(d.oturum, "genc", "Deniz")
        k3 = YetenekKarti(
            kullanici_id=genc3.profil.id, rol_alani="tasarımcı", deneyim_seviyesi="orta"
        )
        d.oturum.add(k3)
        await d.oturum.flush()
        # Eski başlamış ama yeni hareketli (E3) ile yeni başlamış ama eski hareketli (E1).
        d.E1.durum = "kabul_edildi"
        d.E1.son_aktivite_tarihi = simdi - dt.timedelta(days=3)
        e3 = Eslesme(
            ihtiyac_karti_id=d.I1.id,
            yetenek_karti_id=k3.id,
            skor=0.5,
            durum="kabul_edildi",
            son_aktivite_tarihi=simdi,
        )
        d.oturum.add(e3)
        await d.oturum.flush()
        bugun = dt.date.today()
        d.oturum.add_all(
            [
                Isbirligi(eslesme_id=d.E1.id, baslangic_tarihi=bugun, durum="aktif"),
                Isbirligi(
                    eslesme_id=e3.id, baslangic_tarihi=bugun - dt.timedelta(days=10), durum="aktif"
                ),
            ]
        )
        await d.oturum.commit()

        liste = (await istemci.get("/isbirliklerim", headers=d.kurum1.baslik)).json()
        assert [i["genc_adi"] for i in liste] == ["Deniz", "Elif"]

    senaryo(adimlar)
