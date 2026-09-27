"""İşaretleme, tamamlanma kuralı ve ortak görünüm (docs/faz-c-takip.md § 3, § 7).

Gerçek veritabanında, geri alınan işlemde. Dünya: test_sahiplik.py + takip_dunyasi.py.
"""

import datetime as dt

from tests.takip_dunyasi import bildirimleri, isbirligi_ac
from tests.test_sahiplik import durumlar, senaryo


async def aktif_isbirligi(d, adimlar=2):
    """Planı iki tarafça onaylanmış, `adimlar` adımlı iş birliği."""
    isb = await isbirligi_ac(d, adimlar=adimlar)
    simdi = dt.datetime.now(dt.UTC)
    isb.durum = "aktif"
    isb.genc_plan_onayi = isb.kurum_plan_onayi = simdi
    await d.oturum.commit()
    return isb


def _yol(isb, adim=None, ek=""):
    if adim is None:
        return f"/isbirligi/{isb.id}{ek}"
    return f"/isbirligi/{isb.id}/milestone/{adim.id}{ek}"


def test_iki_tarafli_isaret_adimi_ve_isbirligini_tamamlar():
    async def adimlar(istemci, d):
        isb = await aktif_isbirligi(d, adimlar=2)
        birinci, ikinci = sorted(isb.milestonelar, key=lambda m: m.sira)

        # Genç işaretler: adım bekliyor, kuruma "sen de onayla".
        yanit = await istemci.post(_yol(isb, birinci, "/isaretle"), headers=d.genc1.baslik)
        assert yanit.status_code == 200, yanit.text
        adim = yanit.json()["milestonelar"][0]
        assert adim["genc_isaret"] and adim["kurum_isaret"] is None
        assert adim["durum"] == "bekliyor"
        kuruma = await bildirimleri(d, d.kurum1)
        assert [b.tur for b in kuruma] == ["adim_isaretlendi"]
        assert "Elif" in kuruma[0].metin and "Adım 1" in kuruma[0].metin

        # Geri alır, yeniden işaretler (tekrar yan etkisiz).
        geri = await istemci.post(_yol(isb, birinci, "/isareti-geri-al"), headers=d.genc1.baslik)
        assert geri.json()["milestonelar"][0]["genc_isaret"] is None
        await istemci.post(_yol(isb, birinci, "/isaretle"), headers=d.genc1.baslik)
        await istemci.post(_yol(isb, birinci, "/isaretle"), headers=d.genc1.baslik)
        assert len(await bildirimleri(d, d.kurum1)) == 2  # geri alınıp yeniden: 2, tekrar: yok

        # Kurum da işaretler: adım tamamlanır, iki tarafa bildirim; geri açılmaz.
        tamam = await istemci.post(_yol(isb, birinci, "/isaretle"), headers=d.kurum1.baslik)
        assert tamam.json()["milestonelar"][0]["durum"] == "tamamlandi"
        assert tamam.json()["ilerleme"]["tamamlanan"] == 1
        assert tamam.json()["durum"] == "aktif"
        assert (await bildirimleri(d, d.genc1))[-1].tur == "adim_tamamlandi"
        kapali = await istemci.post(_yol(isb, birinci, "/isareti-geri-al"), headers=d.genc1.baslik)
        assert kapali.status_code == 409

        # Son adım: iş birliği kendiliğinden tamamlanır (kural, ajan değil).
        await istemci.post(_yol(isb, ikinci, "/isaretle"), headers=d.kurum1.baslik)
        son = await istemci.post(_yol(isb, ikinci, "/isaretle"), headers=d.genc1.baslik)
        govde = son.json()
        assert govde["durum"] == "tamamlandi"
        assert govde["tamamlanma_tarihi"] is not None
        assert govde["ilerleme"] == {"tamamlanan": 2, "toplam": 2, "geciken": 0}
        gence = (await bildirimleri(d, d.genc1))[-1]
        assert gence.tur == "isbirligi_tamamlandi" and "pilot" in gence.metin
        assert (await bildirimleri(d, d.kurum1))[-1].tur == "isbirligi_tamamlandi"

        # Tamamlanan iş birliğinde her şey 409.
        for istek in (
            istemci.post(_yol(isb, ikinci, "/isareti-geri-al"), headers=d.genc1.baslik),
            istemci.patch(
                _yol(isb, ikinci), headers=d.genc1.baslik, json={"kanit_linki": "https://x.org"}
            ),
            istemci.post(_yol(isb, ek="/plan-onayla"), headers=d.genc1.baslik),
        ):
            assert (await istek).status_code == 409

    senaryo(adimlar)


def test_plan_onaylanmadan_isaretlenmez():
    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d, adimlar=1)
        yanit = await istemci.post(
            _yol(isb, isb.milestonelar[0], "/isaretle"), headers=d.genc1.baslik
        )
        assert yanit.status_code == 409
        assert "onaylanmadan" in yanit.json()["detail"]

    senaryo(adimlar)


def test_ortak_gorunum_gecikme_ve_eposta():
    async def adimlar(istemci, d):
        isb = await aktif_isbirligi(d, adimlar=2)
        birinci, ikinci = sorted(isb.milestonelar, key=lambda m: m.sira)
        birinci.hedef_tarih = dt.date.today() - dt.timedelta(days=3)  # gecikmiş
        ikinci.hedef_tarih = dt.date.today() + dt.timedelta(days=10)
        await d.oturum.commit()

        genc = await istemci.get(_yol(isb), headers=d.genc1.baslik)
        kurum = await istemci.get(_yol(isb), headers=d.kurum1.baslik)
        assert genc.status_code == kurum.status_code == 200
        assert genc.json() == kurum.json()  # iki tarafa birebir aynı görünüm
        govde = genc.json()
        assert [m["gecikmis"] for m in govde["milestonelar"]] == [True, False]
        assert govde["ilerleme"] == {"tamamlanan": 0, "toplam": 2, "geciken": 1}
        assert govde["genc_adi"] == "Elif" and govde["kurum_adi"] == "Koop Bir"
        assert govde["iletisim"]["genc_email"] == d.genc1.hesap.email

        girvak = await istemci.get(_yol(isb), headers=d.girvak.baslik)
        assert girvak.status_code == 200
        assert girvak.json()["iletisim"] is None
        assert d.genc1.hesap.email not in girvak.text

        await durumlar(istemci, "GET", _yol(isb), {None: 401, d.genc2: 404, d.kurum2: 404})

    senaryo(adimlar)


def test_isbirliklerim_ilerleme_ve_girvak_sayilari():
    async def adimlar(istemci, d):
        once = (await istemci.get("/girvak/sayilar", headers=d.girvak.baslik)).json()
        isb = await aktif_isbirligi(d, adimlar=3)
        isb.milestonelar[0].hedef_tarih = dt.date.today() - dt.timedelta(days=1)
        await d.oturum.commit()

        liste = (await istemci.get("/isbirliklerim", headers=d.kurum1.baslik)).json()
        assert liste[0]["durum"] == "aktif"
        assert liste[0]["ilerleme"] == {"tamamlanan": 0, "toplam": 3, "geciken": 1}

        sonra = (await istemci.get("/girvak/sayilar", headers=d.girvak.baslik)).json()
        assert sonra["isbirligi_durumlari"]["aktif"] == once["isbirligi_durumlari"]["aktif"] + 1

    senaryo(adimlar)


def test_isaret_yetkisi():
    async def adimlar(istemci, d):
        isb = await aktif_isbirligi(d, adimlar=1)
        adim = isb.milestonelar[0]
        for ek in ("/isaretle", "/isareti-geri-al"):
            await durumlar(
                istemci,
                "POST",
                _yol(isb, adim, ek),
                {None: 401, d.girvak: 403, d.genc2: 404, d.kurum2: 404},
            )

    senaryo(adimlar)
