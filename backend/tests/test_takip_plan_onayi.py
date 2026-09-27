"""Plan düzenleme ve iki taraflı onay (docs/faz-c-takip.md § 3, § 7), gerçek veritabanında.

Sabitlenenler:
- Taslakta adım eklenir/düzenlenir/silinir; her düzenleme iki onayı sıfırlar.
- İki taraf da onaylayınca iş birliği `aktif`; onaylanmış plan kilitli (409),
  yalnızca kanıt linki eklenebilir.
- Boş plan onaylanamaz; aynı onayın tekrarı yan etkisiz.
- Bildirim karşı tarafa; art arda düzenleme bildirim yağdırmaz.
- Yetki: 401 / 403 (GİRVAK yazamaz) / 404 (başkasının iş birliği ya da adımı).
"""

import datetime as dt

from tests.takip_dunyasi import bildirimleri, isbirligi_ac
from tests.test_sahiplik import durumlar, senaryo


def _yol(isb, ek=""):
    return f"/isbirligi/{isb.id}{ek}"


def test_ekle_duzenle_sil_ve_sira():
    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d, adimlar=2)
        eklenen = await istemci.post(
            _yol(isb, "/milestone-ekle"),
            headers=d.genc1.baslik,
            json={"baslik": "  Canlıya al  ", "aciklama": "", "hedef_tarih": "2026-11-30"},
        )
        assert eklenen.status_code == 201, eklenen.text
        adimlar_ = eklenen.json()["milestonelar"]
        assert [(m["sira"], m["baslik"]) for m in adimlar_] == [
            (0, "Adım 1"),
            (1, "Adım 2"),
            (2, "Canlıya al"),
        ]
        assert adimlar_[2]["aciklama"] is None  # boş açıklama saklanmaz

        ilk = adimlar_[0]["id"]
        guncel = await istemci.patch(
            _yol(isb, f"/milestone/{ilk}"),
            headers=d.kurum1.baslik,
            json={"baslik": "Kayıtları incele", "hedef_tarih": None},
        )
        assert guncel.status_code == 200, guncel.text
        birinci = guncel.json()["milestonelar"][0]
        assert birinci["baslik"] == "Kayıtları incele"
        assert birinci["hedef_tarih"] is None
        assert birinci["aciklama"] is None  # gönderilmedi, değişmedi

        silinen = await istemci.delete(_yol(isb, f"/milestone/{ilk}"), headers=d.genc1.baslik)
        assert [(m["sira"], m["baslik"]) for m in silinen.json()["milestonelar"]] == [
            (0, "Adım 2"),
            (1, "Canlıya al"),
        ]

    senaryo(adimlar)


def test_iki_onay_isbirligini_baslatir_duzenleme_onaylari_sifirlar():
    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d, adimlar=2)
        genc = await istemci.post(_yol(isb, "/plan-onayla"), headers=d.genc1.baslik)
        assert genc.status_code == 200
        assert genc.json()["genc_plan_onayi"] is not None
        assert genc.json()["durum"] == "plan_bekliyor"
        # Kuruma "onayın bekleniyor" bildirimi.
        assert [b.tur for b in await bildirimleri(d, d.kurum1)] == ["plan_onayi"]

        # Tekrar: 200, onay tarihi aynı, yeni bildirim yok.
        yine = await istemci.post(_yol(isb, "/plan-onayla"), headers=d.genc1.baslik)
        assert yine.json()["genc_plan_onayi"] == genc.json()["genc_plan_onayi"]
        assert len(await bildirimleri(d, d.kurum1)) == 1

        # Kurum düzenlerse gencin onayı düşer.
        ilk = genc.json()["milestonelar"][0]["id"]
        duzen = await istemci.patch(
            _yol(isb, f"/milestone/{ilk}"),
            headers=d.kurum1.baslik,
            json={"aciklama": "Defterler tarandı"},
        )
        assert duzen.json()["genc_plan_onayi"] is None
        assert [b.tur for b in await bildirimleri(d, d.genc1)] == ["plan_duzenlendi"]

        # İki taraf onaylayınca aktif; iki tarafa "başladı" bildirimi.
        await istemci.post(_yol(isb, "/plan-onayla"), headers=d.kurum1.baslik)
        son = await istemci.post(_yol(isb, "/plan-onayla"), headers=d.genc1.baslik)
        assert son.json()["durum"] == "aktif"
        assert son.json()["genc_plan_onayi"] and son.json()["kurum_plan_onayi"]
        assert (await bildirimleri(d, d.genc1))[-1].tur == "plan_onaylandi"
        assert (await bildirimleri(d, d.kurum1))[-1].tur == "plan_onaylandi"

    senaryo(adimlar)


def test_onaylanmis_plan_kilitli_yalnizca_kanit_eklenir():
    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d, adimlar=2)
        await istemci.post(_yol(isb, "/plan-onayla"), headers=d.genc1.baslik)
        aktif = await istemci.post(_yol(isb, "/plan-onayla"), headers=d.kurum1.baslik)
        ilk = aktif.json()["milestonelar"][0]["id"]

        for istek in (
            istemci.post(
                _yol(isb, "/milestone-ekle"), headers=d.genc1.baslik, json={"baslik": "x"}
            ),
            istemci.patch(
                _yol(isb, f"/milestone/{ilk}"), headers=d.genc1.baslik, json={"baslik": "x"}
            ),
            istemci.delete(_yol(isb, f"/milestone/{ilk}"), headers=d.genc1.baslik),
            istemci.post(_yol(isb, "/plan-oner"), headers=d.genc1.baslik),
        ):
            yanit = await istek
            assert yanit.status_code == 409, yanit.text
            assert "değiştirilemez" in yanit.json()["detail"]

        kanit = await istemci.patch(
            _yol(isb, f"/milestone/{ilk}"),
            headers=d.genc1.baslik,
            json={"kanit_linki": "https://ornek.org/demo"},
        )
        assert kanit.status_code == 200
        assert kanit.json()["milestonelar"][0]["kanit_linki"] == "https://ornek.org/demo"
        assert kanit.json()["durum"] == "aktif"  # kanıt planı yeniden açmaz

    senaryo(adimlar)


def test_taslakta_kanit_eklenmez_ve_bos_plan_onaylanmaz():
    async def adimlar(istemci, d):
        bos = await isbirligi_ac(d)
        yanit = await istemci.post(_yol(bos, "/plan-onayla"), headers=d.genc1.baslik)
        assert yanit.status_code == 409
        assert "en az bir" in yanit.json()["detail"]

        eklenen = await istemci.post(
            _yol(bos, "/milestone-ekle"), headers=d.genc1.baslik, json={"baslik": "Tek adım"}
        )
        ilk = eklenen.json()["milestonelar"][0]["id"]
        kanit = await istemci.patch(
            _yol(bos, f"/milestone/{ilk}"),
            headers=d.genc1.baslik,
            json={"kanit_linki": "https://ornek.org"},
        )
        assert kanit.status_code == 409

    senaryo(adimlar)


def test_art_arda_duzenleme_tek_bildirim():
    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d)
        for sira in range(3):
            await istemci.post(
                _yol(isb, "/milestone-ekle"),
                headers=d.kurum1.baslik,
                json={"baslik": f"Adım {sira}"},
            )
        assert [b.tur for b in await bildirimleri(d, d.genc1)] == ["plan_duzenlendi"]
        assert await bildirimleri(d, d.kurum1) == []

        # Genç okuyunca bir sonraki düzenleme yine bildirim yazar.
        for b in await bildirimleri(d, d.genc1):
            b.okundu_tarihi = dt.datetime.now(dt.UTC)
        await d.oturum.commit()
        await istemci.post(
            _yol(isb, "/milestone-ekle"), headers=d.kurum1.baslik, json={"baslik": "Bir tane daha"}
        )
        assert len(await bildirimleri(d, d.genc1)) == 2

    senaryo(adimlar)


def test_yetki():
    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d, adimlar=1)
        adim = isb.milestonelar[0].id
        for yontem, yol, govde in (
            ("POST", "/milestone-ekle", {"json": {"baslik": "x"}}),
            ("PATCH", f"/milestone/{adim}", {"json": {"baslik": "x"}}),
            ("DELETE", f"/milestone/{adim}", {}),
            ("POST", "/plan-onayla", {}),
        ):
            await durumlar(
                istemci,
                yontem,
                _yol(isb, yol),
                {None: 401, d.girvak: 403, d.genc2: 404, d.kurum2: 404},
                **govde,
            )

        # Başka iş birliğinin adımı ya da olmayan adım: 404.
        yanit = await istemci.delete(
            _yol(isb, "/milestone/00000000-0000-0000-0000-000000000000"),
            headers=d.genc1.baslik,
        )
        assert yanit.status_code == 404

    senaryo(adimlar)
