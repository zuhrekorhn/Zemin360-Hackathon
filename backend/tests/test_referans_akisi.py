"""Referans akışı (docs/plans/dogrulama-iyilestirme.md § 7, adım 7).

Saf kurallar (form puanı, destek, güç işareti) tabloyla; isteme, engeller, geri
çekme, e-posta ve Canlılık taramasındaki hatırlatma gerçek veritabanında.
"""

import asyncio
import datetime as dt
import uuid
from typing import get_args

import pytest
from sqlalchemy import select

from app.agents.dogrulama import (
    DURUM_BEKLIYOR,
    DURUM_GERI_CEKILDI,
    DURUM_YANIT_YOK,
    DURUM_YANITLANDI,
    HATIRLATMA_GUN,
    ILISKILER,
    YANITLAR,
    ReferansDestegi,
    ReferansYaniti,
    eposta_gucu,
    referans_basligi,
    referans_destegi,
)
from app.api.auth import hesap_olustur
from app.core.kimlik import token_uret
from app.models.bildirim import Bildirim
from app.models.kullanici import Kullanici
from app.models.referans_istegi import ReferansIstegi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.dogrulama import FormCevabi, Iliski
from app.servisler.dogrulama import referans_taramasi
from tests.veritabani import api_istemcisi, geri_alinan_oturum

SIMDI = dt.datetime(2026, 10, 2, 12, tzinfo=dt.UTC)


def _y(iddia=None, pay=None, sonuc=None, puan=None) -> ReferansYaniti:
    return ReferansYaniti(puan=puan, yanit_tarihi=None, iddia=iddia, pay=pay, sonuc=sonuc)


# --- Saf kurallar --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("yanitlar", "beklenen"),
    [
        ([], None),  # yanıt yok: "—", 0 değil (bulgu 19)
        ([_y("evet", "evet", "evet")], 3),
        ([_y("evet", "kismen")], 2),  # (3 + 1) / 2
        ([_y("hayir", "bilmiyorum", "bilmiyorum")], 0),  # bilmiyorum ortalamaya girmez
        ([_y("bilmiyorum", "bilmiyorum")], None),  # hiçbir şey söylemedi
        ([_y("evet"), _y(puan=1)], 2),  # eski 1-5 yanıt eşlemeyle okunur: (3 + 0) / 2 → 1.5 → 2
        ([_y("evet", "evet", "evet"), _y("hayir")], 2),  # kişi başına: (3 + 0) / 2
    ],
)
def test_referans_basligi(yanitlar, beklenen):
    assert referans_basligi(yanitlar) == beklenen


def test_destek_yalnizca_ilgili_sorudaki_evetten():
    assert referans_destegi([_y("evet", pay="kismen", sonuc="evet")]) == ReferansDestegi(
        sonuc=True, pay=False
    )
    # Eski 1-5 yanıt soruya özgü değil: destek sayılmaz.
    assert referans_destegi([_y(puan=5)]) == ReferansDestegi()


@pytest.mark.parametrize(
    ("eposta", "guc"),
    [
        ("hoca@itu.edu.tr", "egitim_eposta"),
        ("mudur@firma.com.tr", "kurumsal_eposta"),
        ("arkadas@gmail.com", None),
        ("Biri@Hotmail.com", None),
    ],
)
def test_eposta_gucu(eposta, guc):
    assert eposta_gucu(eposta) == guc


def test_sema_ve_kural_deger_kumeleri_ayni():
    assert set(get_args(Iliski)) == set(ILISKILER)
    assert set(get_args(FormCevabi)) == set(YANITLAR)


# --- Veritabanlı akış ----------------------------------------------------------------------


async def _genc_ve_kalem(oturum, **kalem):
    hesap = await hesap_olustur(
        oturum,
        email=f"genc-{uuid.uuid4().hex[:10]}@ornek.com",
        sifre="yeterince-uzun",
        rol="genc",
        ad="Elif Şahin",
    )
    kullanici = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
    cikti = SomutCikti(baslik="Kütüphane sistemi", kendi_rolu="Arayüzü yazdım", **kalem)
    oturum.add(
        YetenekKarti(
            kullanici_id=kullanici.id,
            rol_alani="yazılım",
            deneyim_seviyesi="orta",
            somut_ciktilar=[cikti],
        )
    )
    await oturum.commit()
    return hesap, cikti


def _baslik(hesap) -> dict:
    return {"Authorization": f"Bearer {token_uret(hesap.id, hesap.rol)}"}


async def _referanslar(oturum, cikti_id) -> list[ReferansIstegi]:
    return list(
        await oturum.scalars(
            select(ReferansIstegi)
            .where(ReferansIstegi.somut_cikti_id == cikti_id)
            .order_by(ReferansIstegi.olusturma_tarihi)
            .execution_options(populate_existing=True)
        )
    )


def test_referans_istegi_eposta_gonderir_token_yanitta_yok(eposta_gonderilmez):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap, cikti = await _genc_ve_kalem(oturum)
            yanit = await istemci.post(
                f"/dogrulama/kalem/{cikti.id}/referans",
                headers=_baslik(hesap),
                json={"referans_email": "Mudur@Firma.com.tr"},
            )
            assert yanit.status_code == 201
            (istek,) = await _referanslar(oturum, cikti.id)
            # Token ve yanıt linki hiçbir yanıtta yok (bulgu 31).
            assert istek.token not in yanit.text
            assert "yanit_linki" not in yanit.text
            satir = yanit.json()["referanslar"][0]
            assert satir["guc"] == "kurumsal_eposta"
            assert satir["geri_cekilebilir"] is True
            assert istek.gonderim_tarihi is not None

            (eposta,) = eposta_gonderilmez.gonderilenler
            assert eposta.alici.lower() == "mudur@firma.com.tr"
            assert istek.token in eposta.metin
            assert "Elif Şahin" in eposta.metin

            # GİRVAK okuması da token taşımaz.
            girvak = await hesap_olustur(
                oturum,
                email=f"girvak-{uuid.uuid4().hex[:8]}@ornek.com",
                sifre="yeterince-uzun",
                rol="girvak",
                ad="GİRVAK",
            )
            okuma = await istemci.get(f"/dogrulama/kalem/{cikti.id}", headers=_baslik(girvak))
            assert okuma.status_code == 200
            assert istek.token not in okuma.text

    asyncio.run(senaryo())


def test_referans_engelleri(eposta_gonderilmez):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap, cikti = await _genc_ve_kalem(oturum)
            yol, baslik = f"/dogrulama/kalem/{cikti.id}/referans", _baslik(hesap)

            kendi = await istemci.post(
                yol, headers=baslik, json={"referans_email": hesap.email.upper()}
            )
            assert kendi.status_code == 422
            assert "Kendi e-posta" in kendi.json()["detail"]

            ilk = await istemci.post(yol, headers=baslik, json={"referans_email": "a@b.com"})
            assert ilk.status_code == 201
            ikinci = await istemci.post(yol, headers=baslik, json={"referans_email": "A@B.com"})
            assert ikinci.status_code == 409
            assert len(eposta_gonderilmez.gonderilenler) == 1

    asyncio.run(senaryo())


def test_geri_cekme(eposta_gonderilmez):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap, cikti = await _genc_ve_kalem(oturum)
            baskasi, _ = await _genc_ve_kalem(oturum)
            await istemci.post(
                f"/dogrulama/kalem/{cikti.id}/referans",
                headers=_baslik(hesap),
                json={"referans_email": "yanlis@adres.com"},
            )
            (istek,) = await _referanslar(oturum, cikti.id)
            yol = f"/dogrulama/referans/{istek.id}/geri-cek"

            assert (await istemci.post(yol, headers=_baslik(baskasi))).status_code == 404
            assert (await istemci.post(yol)).status_code == 401

            yanit = await istemci.post(yol, headers=_baslik(hesap))
            assert yanit.status_code == 200
            satir = yanit.json()["referanslar"][0]
            assert satir["durum"] == DURUM_GERI_CEKILDI
            assert satir["geri_cekilebilir"] is False
            assert satir["yeniden_istenebilir"] is False
            # Geri çekilen istek kanıt sayılmaz: kart yine kanıt bekliyor.
            assert yanit.json()["kart_kanit_bekleyen"] is True
            # Tekrarı yan etkisiz.
            assert (await istemci.post(yol, headers=_baslik(hesap))).status_code == 200

            # Link artık form açmaz, yanıt kabul edilmez.
            sayfa = await istemci.get(f"/dogrulama/referans/{istek.token}")
            assert sayfa.json()["yanitlanabilir"] is False
            yanit = await istemci.post(
                "/dogrulama/referans-yaniti",
                json={"token": istek.token, "iliski": "diger", "iddia_dogru": "evet"},
            )
            assert yanit.status_code == 409

            # Aynı adrese yeni istek açılabilir (bekleyen yok).
            yeni = await istemci.post(
                f"/dogrulama/kalem/{cikti.id}/referans",
                headers=_baslik(hesap),
                json={"referans_email": "yanlis@adres.com"},
            )
            assert yeni.status_code == 201

    asyncio.run(senaryo())


def test_yanitlanmis_istek_geri_cekilemez():
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap, cikti = await _genc_ve_kalem(oturum)
            istek = ReferansIstegi(somut_cikti_id=cikti.id, referans_email="hoca@ornek.edu.tr")
            oturum.add(istek)
            await oturum.commit()
            yanit = await istemci.post(
                "/dogrulama/referans-yaniti",
                json={
                    "token": istek.token,
                    "iliski": "ogretmen_danisman",
                    "iddia_dogru": "evet",
                    "pay_dogru": "kismen",
                },
            )
            assert yanit.status_code == 200
            geri = await istemci.post(
                f"/dogrulama/referans/{istek.id}/geri-cek", headers=_baslik(hesap)
            )
            assert geri.status_code == 409

            durum = await istemci.get(f"/dogrulama/kalem/{cikti.id}", headers=_baslik(hesap))
            satir = durum.json()["referanslar"][0]
            assert (satir["durum"], satir["iliski"], satir["pay_dogru"]) == (
                DURUM_YANITLANDI,
                "ogretmen_danisman",
                "kismen",
            )
            assert satir["guc"] == "egitim_eposta"
            # (3 + 1) / 2 = 2
            assert durum.json()["guven_skoru"]["ucuncu_taraf_onayi"] == 2

    asyncio.run(senaryo())


def test_tarama_hatirlatir_ve_suresi_dolani_bildirir():
    async def senaryo():
        async with geri_alinan_oturum() as oturum:
            hesap, cikti = await _genc_ve_kalem(oturum)
            gun = dt.timedelta(days=1)
            hatirlatilacak = ReferansIstegi(
                somut_cikti_id=cikti.id,
                referans_email="uc-gun@ornek.com",
                olusturma_tarihi=SIMDI - HATIRLATMA_GUN * gun,
                gonderim_tarihi=SIMDI - HATIRLATMA_GUN * gun,
            )
            eski_yol = ReferansIstegi(  # adım 7'den önce açılmış: e-posta gitmemişti
                somut_cikti_id=cikti.id,
                referans_email="eski@ornek.com",
                olusturma_tarihi=SIMDI - HATIRLATMA_GUN * gun,
            )
            suresi_dolan = ReferansIstegi(
                somut_cikti_id=cikti.id,
                referans_email="yedi-gun@ornek.com",
                olusturma_tarihi=SIMDI - 8 * gun,
                gonderim_tarihi=SIMDI - 8 * gun,
            )
            oturum.add_all([hatirlatilacak, eski_yol, suresi_dolan])
            await oturum.commit()

            sonuc = await referans_taramasi(oturum, SIMDI)
            await oturum.commit()
            assert [e.alici for e in sonuc.hatirlatmalar] == ["uc-gun@ornek.com"]
            assert hatirlatilacak.token in sonuc.hatirlatmalar[0].metin
            assert sonuc.zaman_asimi == 1
            assert hatirlatilacak.hatirlatma_tarihi == SIMDI
            assert (suresi_dolan.durum, eski_yol.durum) == (DURUM_YANIT_YOK, DURUM_BEKLIYOR)

            bildirimler = list(
                await oturum.scalars(select(Bildirim).where(Bildirim.hesap_id == hesap.id))
            )
            assert [b.tur for b in bildirimler] == ["referans_yanit_yok"]

            # İkinci tarama: hatırlatma bir kez, bildirim bir kez.
            ikinci = await referans_taramasi(oturum, SIMDI + dt.timedelta(hours=1))
            assert (ikinci.hatirlatmalar, ikinci.zaman_asimi) == ([], 0)

    asyncio.run(senaryo())


def test_kesif_onayi_kendi_adresini_referans_yapmaz():
    """Sohbetten gelen referans e-postası gencin kendi adresiyse sessizce atılır."""
    from app.api.kesif import _is_kalemi
    from app.schemas.kesif import SomutCiktiTaslagi

    taslak = SomutCiktiTaslagi(baslik="Site", referans_email="Elif@Ornek.com")
    assert _is_kalemi(taslak, "elif@ornek.com").referans_istekleri == []
    kalem = _is_kalemi(taslak, "baska@ornek.com")
    assert [r.referans_email for r in kalem.referans_istekleri] == ["elif@ornek.com"]
    assert kalem.referans_istekleri[0].token
