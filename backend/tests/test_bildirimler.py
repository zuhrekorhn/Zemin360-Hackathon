"""Uygulama içi bildirimler (docs/faz-b-kimlik-ve-dongu.md § 6), gerçek veritabanında.

Dünya test_sahiplik.py'deki: E1 = I1 (kurum1, "Koop Bir") ↔ K1 (genc1, "Elif"),
`onerildi`; E2 = I2 (kurum2) ↔ K2 (genc2, "Can"), `ilgileniliyor`.

Sabitlenenler:
- Her olay doğru kişiye tek bildirim yazar; aynı geçişin tekrarı yeni bildirim yazmaz.
- Bildirim metinleri e-posta taşımaz (adlar serbest).
- Okundu / hepsini oku yalnızca kendi bildirimlerine; sayaç `GET /me`'de.
"""

import uuid

from sqlalchemy import select

from app.db.base import EMBEDDING_DIM
from app.models.bildirim import Bildirim
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.referans_istegi import ReferansIstegi
from app.models.yetenek_karti import YetenekKarti
from app.servisler import eslestirme as eslestirme_servisi
from tests.test_sahiplik import _hesap, durumlar, senaryo

VEKTOR = [1.0] + [0.0] * (EMBEDDING_DIM - 1)


async def _bildirimler(d, kisi):
    return list(await d.oturum.scalars(select(Bildirim).where(Bildirim.hesap_id == kisi.hesap.id)))


async def _okunmamis(istemci, kisi):
    return (await istemci.get("/me", headers=kisi.baslik)).json()["okunmamis_bildirim"]


def test_ilgi_kabul_ve_red_bildirimleri():
    async def adimlar(istemci, d):
        e1 = {"eslesme_id": str(d.E1.id)}
        for _ in range(2):  # ikincisi çift tıklama
            yanit = await istemci.post(
                "/eslestirme/ilgileniyorum", headers=d.kurum1.baslik, json=e1
            )
            assert yanit.status_code == 200

        ilgi = await _bildirimler(d, d.genc1)
        assert [(b.tur, b.eslesme_id) for b in ilgi] == [("ilgi", d.E1.id)]
        assert "Koop Bir" in ilgi[0].metin
        assert "backend geliştirici" in ilgi[0].metin
        assert await _okunmamis(istemci, d.genc1) == 1

        for _ in range(2):
            yanit = await istemci.post(f"/eslestirme/{d.E1.id}/kabul", headers=d.genc1.baslik)
            assert yanit.status_code == 200
        kabul = await _bildirimler(d, d.kurum1)
        assert [b.tur for b in kabul] == ["kabul"]
        assert kabul[0].metin == ("Elif ilginizi kabul etti; iletişim bilgileriniz paylaşıldı.")

        red = await istemci.post(f"/eslestirme/{d.E2.id}/red", headers=d.genc2.baslik)
        assert red.status_code == 200
        reddedilen = await _bildirimler(d, d.kurum2)
        assert [b.metin for b in reddedilen] == ["Can bu eşleşmeyi şu an kabul etmedi."]

        # Hiçbir bildirim metninde e-posta yok.
        epostalar = {k.hesap.email for k in (d.genc1, d.genc2, d.kurum1, d.kurum2)}
        tumu = [b.metin for k in (d.genc1, d.kurum1, d.kurum2) for b in await _bildirimler(d, k)]
        assert not any(e in m for e in epostalar for m in tumu)

    senaryo(adimlar)


def test_gecersiz_gecis_bildirim_yazmaz():
    async def adimlar(istemci, d):
        yanit = await istemci.post(f"/eslestirme/{d.E2.id}/red", headers=d.genc2.baslik)
        assert yanit.status_code == 200
        onceki = len(await _bildirimler(d, d.kurum2))
        yanit = await istemci.post(f"/eslestirme/{d.E2.id}/kabul", headers=d.genc2.baslik)
        assert yanit.status_code == 409
        assert len(await _bildirimler(d, d.kurum2)) == onceki

    senaryo(adimlar)


def test_liste_okundu_ve_hepsini_oku():
    async def adimlar(istemci, d):
        for metin in ("birinci", "ikinci", "üçüncü"):
            d.oturum.add(Bildirim(hesap_id=d.genc1.hesap.id, tur="ilgi", metin=metin))
        d.oturum.add(Bildirim(hesap_id=d.genc2.hesap.id, tur="ilgi", metin="başkasının"))
        await d.oturum.commit()

        liste = (await istemci.get("/bildirimler", headers=d.genc1.baslik)).json()
        assert sorted(b["metin"] for b in liste) == ["birinci", "ikinci", "üçüncü"]
        assert await _okunmamis(istemci, d.genc1) == 3

        ilk = liste[0]["id"]
        # Başkasının bildirimi 404; token'sız 401.
        await durumlar(
            istemci,
            "POST",
            f"/bildirimler/{ilk}/okundu",
            {None: 401, d.genc2: 404, d.kurum1: 404, d.girvak: 404},
        )
        okundu = await istemci.post(f"/bildirimler/{ilk}/okundu", headers=d.genc1.baslik)
        assert okundu.status_code == 200
        ilk_tarih = okundu.json()["okundu_tarihi"]
        assert ilk_tarih is not None
        # Tekrar: ilk okunma tarihi korunur.
        yine = await istemci.post(f"/bildirimler/{ilk}/okundu", headers=d.genc1.baslik)
        assert yine.json()["okundu_tarihi"] == ilk_tarih
        assert await _okunmamis(istemci, d.genc1) == 2

        hepsi = await istemci.post("/bildirimler/hepsini-oku", headers=d.genc1.baslik)
        assert hepsi.json() == {"okunan": 2}
        assert await _okunmamis(istemci, d.genc1) == 0
        # Başkasınınkine dokunmadı.
        assert await _okunmamis(istemci, d.genc2) == 1

        # GİRVAK'ın da bildirim uçları var (kendi, boş).
        await durumlar(istemci, "GET", "/bildirimler", {None: 401, d.girvak: 200})

    senaryo(adimlar)


def test_referans_yaniti_gence_bildirim_yazar():
    async def adimlar(istemci, d):
        referans = ReferansIstegi(somut_cikti_id=d.C1.id, referans_email="hoca@ornek.edu")
        d.oturum.add(referans)
        await d.oturum.commit()

        yanit = await istemci.post(
            "/dogrulama/referans-yaniti", json={"token": referans.token, "puan": 4}
        )
        assert yanit.status_code == 200
        bildirimler = await _bildirimler(d, d.genc1)
        assert [b.tur for b in bildirimler] == ["referans_yaniti"]
        assert "hoca@ornek.edu" not in bildirimler[0].metin

    senaryo(adimlar)


def test_pipeline_yalnizca_yeni_oneri_icin_bildirim_yazar(monkeypatch):
    """İlk hesap yeni önerileri sayar; ikinci hesapta yeni yok, bildirim yok."""

    async def gerekce_yok(_ihtiyac, _aday):
        return None

    monkeypatch.setattr(eslestirme_servisi, "gerekce_uret", gerekce_yok)

    async def adimlar(istemci, d):
        kurum = await _hesap(d.oturum, "kurum", "Vektör Koop")
        genc = await _hesap(d.oturum, "genc", "Ayşe")
        # Rastgele bir yön: yerel veritabanındaki gerçek kartlarla karışmasın.
        vektor = [0.0] * EMBEDDING_DIM
        vektor[uuid.uuid4().int % EMBEDDING_DIM] = 1.0
        d.oturum.add_all(
            [
                IhtiyacKarti(kurum_id=kurum.profil.id, problem_tanimi="p", embedding=vektor),
                YetenekKarti(
                    kullanici_id=genc.profil.id,
                    rol_alani="r",
                    deneyim_seviyesi="orta",
                    embedding=vektor,
                ),
            ]
        )
        await d.oturum.commit()

        ilk = await istemci.post("/eslestirme/calistir", headers=kurum.baslik, json={})
        assert ilk.status_code == 200
        sayi = len(ilk.json()["oneriler"])
        assert sayi >= 1
        bildirimler = await _bildirimler(d, kurum)
        assert [b.metin for b in bildirimler] == [f"İhtiyacınız için {sayi} yeni aday var."]

        ikinci = await istemci.post("/eslestirme/calistir", headers=kurum.baslik, json={})
        assert ikinci.status_code == 200
        assert len(await _bildirimler(d, kurum)) == 1

    senaryo(adimlar)


def test_ayni_islemde_yazilan_bildirimler_en_yeni_once_siralanir():
    """`now()` işlem başlangıcını döndüğü için aynı işlemdeki bildirimler eşit
    zamanlı kalıyor, sıra belirsizleşiyordu; zaman damgası INSERT anında
    `clock_timestamp()` ile atanıyor."""
    from app.api.bildirimler import bildirim_ekle

    async def adimlar(istemci, d):
        for metin in ("birinci", "ikinci", "üçüncü"):
            bildirim_ekle(d.oturum, d.genc1.hesap.id, "ilgi", metin)
            await d.oturum.flush()
        await d.oturum.commit()
        liste = (await istemci.get("/bildirimler", headers=d.genc1.baslik)).json()
        assert [b["metin"] for b in liste] == ["üçüncü", "ikinci", "birinci"]

    senaryo(adimlar)
