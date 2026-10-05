"""İlan kapatma (docs/plans/firma-akisi.md § 0 karar 7, § 7).

Kural `ihtiyaci_kapat`'ta (tests/test_ilgi_durumu.py); burada uç: yetki,
neden, tekrar, bildirimde neden olmaması, GİRVAK sayısı ve kapalı ilana
öneri yazılmaması.
"""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import select

from app.core.ilan import KAPANMA_NEDENLERI
from app.db.base import EMBEDDING_DIM
from app.models.bildirim import TUR_FIRSAT_KAPANDI, Bildirim
from app.models.eslesme import Eslesme
from app.models.ihtiyac_karti import IhtiyacKarti
from app.servisler import eslestirme as eslestirme_servisi
from tests.test_sahiplik import durumlar, senaryo

ONAY = {"iletisim_onayi": True}


def _yol(d) -> str:
    return f"/ihtiyac-kartlari/{d.I1.id}/kapat"


def test_kapanma_nedenleri():
    assert KAPANMA_NEDENLERI == (
        "platformda_bulundu",
        "baska_yoldan_bulundu",
        "vazgecildi",
        "hatali_girildi",
    )


def test_kapatma_yetkisi():
    """401 token yok, 403 genç/GİRVAK (yazma firmanın işi), 404 başka firmanın ilanı."""

    async def adimlar(istemci, d):
        await durumlar(
            istemci,
            "POST",
            _yol(d),
            {None: 401, d.genc1: 403, d.girvak: 403, d.kurum2: 404},
            json={"neden": "vazgecildi"},
        )
        ilan = await d.oturum.get(IhtiyacKarti, d.I1.id)
        await d.oturum.refresh(ilan)
        assert ilan.durum == "acik"

    senaryo(adimlar)


def test_neden_zorunlu_ve_kume_disi_422():
    async def adimlar(istemci, d):
        for govde in ({}, {"neden": "bilmiyorum"}, {"neden": "vazgecildi", "not": "x"}):
            yanit = await istemci.post(_yol(d), headers=d.kurum1.baslik, json=govde)
            assert yanit.status_code == 422, govde

    senaryo(adimlar)


def test_kapatma_bekleyenleri_kapatir_neden_gizli_tekrar_yan_etkisiz():
    async def adimlar(istemci, d):
        # E1'e genç ilgi gösterdi: kapatınca gence nötr bildirim gider.
        await istemci.post(f"/eslestirme/{d.E1.id}/genc-ilgi", headers=d.genc1.baslik, json=ONAY)

        yanit = await istemci.post(
            _yol(d), headers=d.kurum1.baslik, json={"neden": "platformda_bulundu"}
        )
        assert yanit.status_code == 200
        govde = yanit.json()
        assert govde["durum"] == "kapandi"
        assert "kapanma_nedeni" not in govde  # yalnızca GİRVAK görür

        e1 = await d.oturum.scalar(
            select(Eslesme).where(Eslesme.id == d.E1.id).execution_options(populate_existing=True)
        )
        assert e1.durum == "kapandi"
        bildirimler = list(
            await d.oturum.scalars(
                select(Bildirim).where(
                    Bildirim.hesap_id == d.genc1.hesap.id, Bildirim.tur == TUR_FIRSAT_KAPANDI
                )
            )
        )
        assert len(bildirimler) == 1
        assert "platform" not in bildirimler[0].metin.lower()

        # Tekrar: 200, ilk neden korunur, ikinci bildirim yok.
        tekrar = await istemci.post(_yol(d), headers=d.kurum1.baslik, json={"neden": "vazgecildi"})
        assert tekrar.status_code == 200
        ilan = await d.oturum.scalar(
            select(IhtiyacKarti)
            .where(IhtiyacKarti.id == d.I1.id)
            .execution_options(populate_existing=True)
        )
        assert ilan.kapanma_nedeni == "platformda_bulundu"
        assert ilan.kapanma_tarihi is not None
        sayi = len(
            list(
                await d.oturum.scalars(
                    select(Bildirim).where(
                        Bildirim.hesap_id == d.genc1.hesap.id, Bildirim.tur == TUR_FIRSAT_KAPANDI
                    )
                )
            )
        )
        assert sayi == 1

        # Panel kapalı ilanı durumuyla görür.
        me = (await istemci.get("/me", headers=d.kurum1.baslik)).json()
        assert {k["id"]: k["durum"] for k in me["ihtiyac_kartlari"]}[str(d.I1.id)] == "kapandi"

        # GİRVAK sayısı nedenle.
        sayilar = (await istemci.get("/girvak/sayilar", headers=d.girvak.baslik)).json()
        assert sayilar["kapanan_ihtiyaclar"]["platformda_bulundu"] == 1

        # Giriş hatası ayrı sayılır, "vazgeçildi"yi şişirmez.
        hatali = await istemci.post(
            f"/ihtiyac-kartlari/{d.I2.id}/kapat",
            headers=d.kurum2.baslik,
            json={"neden": "hatali_girildi"},
        )
        assert hatali.status_code == 200
        sayilar = (await istemci.get("/girvak/sayilar", headers=d.girvak.baslik)).json()
        assert sayilar["kapanan_ihtiyaclar"]["hatali_girildi"] == 1
        assert sayilar["kapanan_ihtiyaclar"]["vazgecildi"] == 0

    senaryo(adimlar)


def test_kapali_ilana_pipeline_oneri_yazmaz():
    """Pipeline kilidi aldıktan sonra durumu yeniden okur (kapatma aynı kilidi alıyor)."""

    async def adimlar(istemci, d):
        ilan = await d.oturum.get(IhtiyacKarti, d.I1.id)
        ilan.embedding = [0.0] * EMBEDDING_DIM
        await d.oturum.commit()
        await istemci.post(_yol(d), headers=d.kurum1.baslik, json={"neden": "vazgecildi"})

        # Bayat görünüm: çağıran kapatmadan önce okumuş, hâlâ "acik" görüyor.
        bayat = SimpleNamespace(
            id=ilan.id,
            kurum_id=ilan.kurum_id,
            embedding=ilan.embedding,
            durum="acik",
            aranan="genc",
        )
        try:
            await eslestirme_servisi.pipeline_calistir(d.oturum, bayat)
        except Exception as hata:  # noqa: BLE001 — beklenen 409
            assert getattr(hata, "status_code", None) == 409
        else:
            raise AssertionError("kapalı ilanda pipeline çalıştı")

    senaryo(adimlar)
