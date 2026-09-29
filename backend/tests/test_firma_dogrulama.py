"""Firma doğrulaması (docs/plans/firma-akisi.md § 0 kararlar 6, 15, 17; § 6).

Sistem ipucu verir (ağ isteği yok), GİRVAK karar verir. Doğrulanmamış firma
her şeyi kullanır; yalnızca işareti olmaz.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.core.firma_dogrulama import (
    EPOSTA_YOK,
    SITE_YOK,
    UCRETSIZ_EPOSTA,
    UYUSMUYOR,
    UYUSUYOR,
    alan_adi_ipucu,
    dogrulama_sifirlanir_mi,
    eposta_alan_adi,
    site_alan_adi,
)
from app.models.bildirim import TUR_FIRMA_DOGRULANDI, Bildirim
from app.models.kurum import Kurum
from tests.test_sahiplik import durumlar, senaryo

# --- Saf kurallar ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("eposta", "site", "beklenen"),
    [
        ("ayse@marketx.com", "https://marketx.com", UYUSUYOR),
        ("ayse@marketx.com", "www.marketx.com/", UYUSUYOR),
        ("ayse@MarketX.com", "marketx.com", UYUSUYOR),
        # Alt alan adı iki yönde de uyuşur.
        ("ayse@ik.marketx.com.tr", "marketx.com.tr", UYUSUYOR),
        ("ayse@marketx.com.tr", "https://shop.marketx.com.tr/tr", UYUSUYOR),
        ("ayse@marketx.com", "markety.com", UYUSMUYOR),
        # Sonek benzerliği uyuşma değil: "xmarketx.com" "marketx.com"un alt alanı değil.
        ("ayse@xmarketx.com", "marketx.com", UYUSMUYOR),
        ("ayse@gmail.com", "marketx.com", UCRETSIZ_EPOSTA),
        ("ayse@hotmail.com.tr", None, UCRETSIZ_EPOSTA),
        ("ayse@marketx.com", None, SITE_YOK),
        ("ayse@marketx.com", "  ", SITE_YOK),
        (None, "marketx.com", EPOSTA_YOK),
    ],
)
def test_alan_adi_ipucu(eposta, site, beklenen):
    assert alan_adi_ipucu(eposta, site) == beklenen


def test_alan_adlari():
    assert eposta_alan_adi("a@WWW.Ornek.com.") == "ornek.com"
    assert eposta_alan_adi("bozuk") is None
    assert site_alan_adi("http://www.ornek.com:8080/x?y") == "ornek.com"
    assert site_alan_adi(None) is None


def test_dogrulama_yalnizca_alan_adi_degisince_sifirlanir():
    assert not dogrulama_sifirlanir_mi("https://marketx.com", "https://marketx.com/")
    assert not dogrulama_sifirlanir_mi("https://marketx.com", "www.marketx.com")
    assert dogrulama_sifirlanir_mi("https://marketx.com", "https://baska.com")
    assert dogrulama_sifirlanir_mi(None, "marketx.com")
    assert dogrulama_sifirlanir_mi("marketx.com", None)


# --- Gerçek veritabanı -----------------------------------------------------------------


async def _kurum(d, kurum_id) -> Kurum:
    return await d.oturum.scalar(
        select(Kurum).where(Kurum.id == kurum_id).execution_options(populate_existing=True)
    )


async def _bildirim_sayisi(d, hesap_id) -> int:
    return await d.oturum.scalar(
        select(func.count())
        .select_from(Bildirim)
        .where(Bildirim.hesap_id == hesap_id, Bildirim.tur == TUR_FIRMA_DOGRULANDI)
    )


def test_uclar_yalnizca_girvak():
    async def adimlar(istemci, d):
        yol = f"/girvak/firmalar/{d.kurum1.profil.id}/dogrula"
        await durumlar(istemci, "GET", "/girvak/firmalar", {None: 401, d.genc1: 403, d.kurum1: 403})
        await durumlar(
            istemci,
            "POST",
            yol,
            {None: 401, d.genc1: 403, d.kurum1: 403},
            json={"karar": "dogrulandi"},
        )
        assert (await _kurum(d, d.kurum1.profil.id)).dogrulama_durumu == "bekliyor"

    senaryo(adimlar)


def test_liste_ipucu_ve_tam_eposta_yok():
    async def adimlar(istemci, d):
        kurum = await _kurum(d, d.kurum1.profil.id)
        kurum.iletisim_email = "ayse@koopbir.org"
        kurum.web_sitesi = "https://www.koopbir.org"
        await d.oturum.commit()

        yanit = await istemci.get("/girvak/firmalar", headers=d.girvak.baslik)
        assert yanit.status_code == 200
        satirlar = {s["kurum_id"]: s for s in yanit.json()}
        satir = satirlar[str(d.kurum1.profil.id)]
        assert satir["ipucu"] == "uyusuyor"
        assert satir["eposta_alan_adi"] == "koopbir.org"
        assert "ayse@" not in yanit.text  # tam e-posta dönmez
        assert str(d.kurum2.profil.id) in satirlar

    senaryo(adimlar)


def test_karar_bildirim_tekrar_ve_isaret():
    async def adimlar(istemci, d):
        yol = f"/girvak/firmalar/{d.kurum1.profil.id}/dogrula"
        yanit = await istemci.post(yol, headers=d.girvak.baslik, json={"karar": "dogrulandi"})
        assert yanit.status_code == 200
        assert yanit.json()["dogrulama_durumu"] == "dogrulandi"
        assert yanit.json()["dogrulama_tarihi"] is not None
        assert await _bildirim_sayisi(d, d.kurum1.hesap.id) == 1

        # Tekrar: 200, ikinci bildirim yok.
        tekrar = await istemci.post(yol, headers=d.girvak.baslik, json={"karar": "dogrulandi"})
        assert tekrar.status_code == 200
        assert await _bildirim_sayisi(d, d.kurum1.hesap.id) == 1

        # İşaret: firmanın profilinde ve ilanın firma bilgisinde (gence görünen).
        profil = (await istemci.get("/kurum/profil", headers=d.kurum1.baslik)).json()
        assert profil["dogrulandi"] is True
        ilan = (await istemci.get(f"/ihtiyac-kartlari/{d.I1.id}", headers=d.genc1.baslik)).json()
        assert ilan["kurum"]["dogrulandi"] is True
        assert "dogrulama_durumu" not in ilan["kurum"]

        # Listeler: artık onay bekleyenlerde değil, doğrulananlarda.
        bekleyen = await istemci.get("/girvak/firmalar", headers=d.girvak.baslik)
        assert str(d.kurum1.profil.id) not in {s["kurum_id"] for s in bekleyen.json()}
        dogrulanan = await istemci.get(
            "/girvak/firmalar", params={"durum": "dogrulandi"}, headers=d.girvak.baslik
        )
        assert str(d.kurum1.profil.id) in {s["kurum_id"] for s in dogrulanan.json()}

    senaryo(adimlar)


def test_simdilik_degil_sessiz_ve_firma_ayirt_etmez():
    async def adimlar(istemci, d):
        yol = f"/girvak/firmalar/{d.kurum2.profil.id}/dogrula"
        yanit = await istemci.post(yol, headers=d.girvak.baslik, json={"karar": "simdilik_degil"})
        assert yanit.status_code == 200
        assert await _bildirim_sayisi(d, d.kurum2.hesap.id) == 0
        profil = (await istemci.get("/kurum/profil", headers=d.kurum2.baslik)).json()
        assert profil["dogrulandi"] is False
        assert "dogrulama_durumu" not in profil

    senaryo(adimlar)


def test_gecersiz_karar_ve_bilinmeyen_firma():
    async def adimlar(istemci, d):
        yol = f"/girvak/firmalar/{d.kurum1.profil.id}/dogrula"
        for govde in ({}, {"karar": "bekliyor"}, {"karar": "dogrulandi", "not": "x"}):
            cevap = await istemci.post(yol, headers=d.girvak.baslik, json=govde)
            assert cevap.status_code == 422, govde
        bilinmeyen = await istemci.post(
            f"/girvak/firmalar/{d.I1.id}/dogrula",
            headers=d.girvak.baslik,
            json={"karar": "dogrulandi"},
        )
        assert bilinmeyen.status_code == 404
        gecersiz_filtre = await istemci.get(
            "/girvak/firmalar", params={"durum": "hepsi"}, headers=d.girvak.baslik
        )
        assert gecersiz_filtre.status_code == 422

    senaryo(adimlar)


def test_site_degisince_dogrulama_yeniden_beklenir():
    async def adimlar(istemci, d):
        kurum = await _kurum(d, d.kurum1.profil.id)
        kurum.web_sitesi = "https://koopbir.org"
        await d.oturum.commit()
        await istemci.post(
            f"/girvak/firmalar/{d.kurum1.profil.id}/dogrula",
            headers=d.girvak.baslik,
            json={"karar": "dogrulandi"},
        )

        # Aynı alan adının yazım farkı ve başka alanlar sıfırlamaz.
        for govde in ({"web_sitesi": "www.koopbir.org/"}, {"tanitim": "Yeni tanıtım"}):
            cevap = await istemci.patch("/kurum/profil", headers=d.kurum1.baslik, json=govde)
            assert cevap.json()["dogrulandi"] is True, govde

        cevap = await istemci.patch(
            "/kurum/profil", headers=d.kurum1.baslik, json={"web_sitesi": "baska.com"}
        )
        assert cevap.json()["dogrulandi"] is False
        kurum = await _kurum(d, d.kurum1.profil.id)
        assert kurum.dogrulama_durumu == "bekliyor"
        assert kurum.dogrulama_tarihi is None

    senaryo(adimlar)
