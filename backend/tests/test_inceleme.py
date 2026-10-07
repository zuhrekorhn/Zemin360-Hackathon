"""GİRVAK inceleme kuyruğu (docs/dogrulama.md § 9): saf geçiş kuralı,
tek açık işaret, kuyruk ve karar uçları (401 / 403 / 404 / 409), bildirim.

Dünya: test_sahiplik.py — genc1 "Elif"in kartı K1 ve çalışması C1 "Kütüphane sistemi".
"""

import pytest
from sqlalchemy import func, select

from app.agents.inceleme_durumu import (
    ACIK,
    DOGRULANAMADI,
    KAPANDI,
    GecersizKarar,
    inceleme_gecisi,
)
from app.models.bildirim import TUR_INCELEME_SONUCU, Bildirim
from app.models.inceleme_isareti import TUR_ITIRAZ_SINIRI
from app.servisler import inceleme
from tests.test_sahiplik import durumlar, senaryo


@pytest.mark.parametrize(
    ("durum", "karar", "beklenen"),
    [
        (ACIK, KAPANDI, KAPANDI),
        (ACIK, DOGRULANAMADI, DOGRULANAMADI),
        (KAPANDI, KAPANDI, None),  # tekrar: yan etkisiz
        (DOGRULANAMADI, DOGRULANAMADI, None),
    ],
)
def test_gecis_tablosu(durum, karar, beklenen):
    assert inceleme_gecisi(durum, karar) == beklenen


@pytest.mark.parametrize(("durum", "karar"), [(KAPANDI, DOGRULANAMADI), (DOGRULANAMADI, KAPANDI)])
def test_kapanmis_isarete_baska_karar_gecersiz(durum, karar):
    with pytest.raises(GecersizKarar):
        inceleme_gecisi(durum, karar)


def test_gecersiz_karar_degeri():
    with pytest.raises(ValueError):
        inceleme_gecisi(ACIK, ACIK)


async def _bildirim_sayisi(oturum, hesap_id) -> int:
    return await oturum.scalar(
        select(func.count())
        .select_from(Bildirim)
        .where(Bildirim.hesap_id == hesap_id, Bildirim.tur == TUR_INCELEME_SONUCU)
    )


def test_ayni_konuya_tek_acik_isaret_ayrinti_birlesir():
    async def adimlar(_istemci, d):
        def birlestir(eski, yeni):
            return {"notlar": [*eski.get("notlar", []), *yeni["notlar"]]}

        bir, yeni_mi = await inceleme.isaret_ac(
            d.oturum,
            TUR_ITIRAZ_SINIRI,
            d.genc1.profil.id,
            somut_cikti_id=d.C1.id,
            ayrinti={"notlar": ["a"]},
            birlestir=birlestir,
        )
        assert yeni_mi
        iki, yeni_mi = await inceleme.isaret_ac(
            d.oturum,
            TUR_ITIRAZ_SINIRI,
            d.genc1.profil.id,
            somut_cikti_id=d.C1.id,
            ayrinti={"notlar": ["b"]},
            birlestir=birlestir,
        )
        assert not yeni_mi and iki.id == bir.id
        assert iki.ayrinti == {"notlar": ["a", "b"]}

        # Kapanınca aynı konu için yeni işaret açılabilir.
        bir.durum = KAPANDI
        await d.oturum.flush()
        uc, yeni_mi = await inceleme.isaret_ac(
            d.oturum, TUR_ITIRAZ_SINIRI, d.genc1.profil.id, somut_cikti_id=d.C1.id
        )
        assert yeni_mi and uc.id != bir.id

    senaryo(adimlar)


def test_kuyruk_ve_karar_uclari():
    async def adimlar(istemci, d):
        isaret, _ = await inceleme.isaret_ac(
            d.oturum,
            TUR_ITIRAZ_SINIRI,
            d.genc1.profil.id,
            somut_cikti_id=d.C1.id,
            ayrinti={"itiraz_notlari": ["Repo benim"]},
        )
        await d.oturum.commit()

        await durumlar(
            istemci,
            "GET",
            "/girvak/inceleme",
            {None: 401, d.genc1: 403, d.kurum1: 403, d.girvak: 200},
        )
        liste = (await istemci.get("/girvak/inceleme", headers=d.girvak.baslik)).json()
        (satir,) = [s for s in liste if s["id"] == str(isaret.id)]
        assert satir["genc_adi"] == "Elif"
        assert satir["kart_id"] == str(d.K1.id)
        assert satir["cikti_basligi"] == "Kütüphane sistemi"
        assert satir["ayrinti"] == {"itiraz_notlari": ["Repo benim"]}

        yol = f"/girvak/inceleme/{isaret.id}/karar"
        govde = {"json": {"karar": "dogrulanamadi", "girvak_notu": "Repo başka hesapta"}}
        await durumlar(istemci, "POST", yol, {None: 401, d.genc1: 403}, **govde)

        once = await _bildirim_sayisi(d.oturum, d.genc1.hesap.id)
        yanit = await istemci.post(yol, headers=d.girvak.baslik, **govde)
        assert yanit.status_code == 200
        assert yanit.json()["durum"] == "dogrulanamadi"
        assert yanit.json()["girvak_notu"] == "Repo başka hesapta"
        assert await _bildirim_sayisi(d.oturum, d.genc1.hesap.id) == once + 1
        metin = await d.oturum.scalar(
            select(Bildirim.metin)
            .where(Bildirim.hesap_id == d.genc1.hesap.id, Bildirim.tur == TUR_INCELEME_SONUCU)
            .order_by(Bildirim.olusturma_tarihi.desc())
            .limit(1)
        )
        assert "“Kütüphane sistemi” çalışmanı" in metin
        assert "Repo başka hesapta" in metin

        # Tekrar 200, bildirim yok; başka karar 409; kapanan listede.
        assert (await istemci.post(yol, headers=d.girvak.baslik, **govde)).status_code == 200
        assert await _bildirim_sayisi(d.oturum, d.genc1.hesap.id) == once + 1
        yanit = await istemci.post(yol, headers=d.girvak.baslik, json={"karar": "kapandi"})
        assert yanit.status_code == 409
        kapananlar = await istemci.get(
            "/girvak/inceleme", params={"durum": "dogrulanamadi"}, headers=d.girvak.baslik
        )
        assert str(isaret.id) in {s["id"] for s in kapananlar.json()}

        yanit = await istemci.post(
            f"/girvak/inceleme/{d.C1.id}/karar", headers=d.girvak.baslik, json={"karar": "kapandi"}
        )
        assert yanit.status_code == 404

    senaryo(adimlar)
