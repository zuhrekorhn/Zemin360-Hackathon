"""Kayıt e-postasının doğrulanması (docs/dogrulama.md § 6.3), gerçek
veritabanında: kayıt bağlantıyı gönderir, bağlantı hesabı doğrular, tekrarı yan
etkisiz, süresi dolan ya da yenisiyle geçersizleşen bağlantı 400, yeniden gönderme
kuralları (401 / 409 / 429)."""

import asyncio
import datetime as dt
import uuid
from urllib.parse import parse_qs, urlparse

from sqlalchemy import update

from app.models.eposta_dogrulama import EpostaDogrulama
from app.models.hesap import Hesap
from tests.sahte_hesap import FIRMA_KAYIT_EKI, GENC_KAYIT_EKI
from tests.veritabani import api_istemcisi, geri_alinan_oturum


def _token(eposta) -> str:
    satir = next(s for s in eposta.metin.splitlines() if "/eposta-dogrula?" in s)
    return parse_qs(urlparse(satir.strip()).query)["token"][0]


async def _kayit(istemci, rol="genc", eki=GENC_KAYIT_EKI):
    yanit = await istemci.post(
        "/auth/kayit",
        json={
            "email": f"{uuid.uuid4().hex[:8]}@ornek.com",
            "sifre": "yeterince-uzun-sifre",
            "rol": rol,
            "ad": "Elif Yılmaz",
            **eki,
        },
    )
    assert yanit.status_code == 201
    return {"Authorization": f"Bearer {yanit.json()['token']}"}


def test_kayit_baglanti_gonderir_baglanti_dogrular_tekrari_yan_etkisiz(eposta_gonderilmez):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik = await _kayit(istemci)
            me = (await istemci.get("/me", headers=baslik)).json()
            assert me["eposta_dogrulandi"] is False

            (eposta,) = eposta_gonderilmez.gonderilenler
            assert eposta.alici == me["email"]
            assert "doğrulamak için bu bağlantıyı aç:" in eposta.metin  # gence "sen"
            token = _token(eposta)

            for _ in range(2):  # ikinci açılış (çift tıklama) da 200
                yanit = await istemci.post("/auth/eposta-dogrula", json={"token": token})
                assert yanit.status_code == 200
                assert yanit.json() == {"eposta_dogrulandi": True}
            assert (await istemci.get("/me", headers=baslik)).json()["eposta_dogrulandi"]

            # Doğrulanmış hesap yeni bağlantı istemez.
            yanit = await istemci.post("/auth/eposta-dogrulama/yeniden", headers=baslik)
            assert yanit.status_code == 409

    asyncio.run(senaryo())


def test_firmaya_siz_hitabi(eposta_gonderilmez):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            await _kayit(istemci, rol="kurum", eki=FIRMA_KAYIT_EKI)
            (eposta,) = eposta_gonderilmez.gonderilenler
            assert "doğrulamak için bu bağlantıyı açın:" in eposta.metin
            assert "adresinizi" in eposta.konu

    asyncio.run(senaryo())


def test_gecersiz_ve_suresi_dolmus_baglanti_400(eposta_gonderilmez):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik = await _kayit(istemci)
            yanit = await istemci.post("/auth/eposta-dogrula", json={"token": "uydurma"})
            assert yanit.status_code == 400
            assert "geçersiz ya da süresi dolmuş" in yanit.json()["detail"]

            await oturum.execute(
                update(EpostaDogrulama).values(
                    son_gecerlilik=dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1),
                    olusturma_tarihi=dt.datetime.now(dt.UTC) - dt.timedelta(days=1),
                )
            )
            eski = _token(eposta_gonderilmez.gonderilenler[0])
            yanit = await istemci.post("/auth/eposta-dogrula", json={"token": eski})
            assert yanit.status_code == 400
            assert not (await istemci.get("/me", headers=baslik)).json()["eposta_dogrulandi"]

    asyncio.run(senaryo())


def test_yeniden_gonderme_eskiyi_gecersiz_kilar_ve_sikligi_sinirlar(eposta_gonderilmez):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            assert (await istemci.post("/auth/eposta-dogrulama/yeniden")).status_code == 401
            baslik = await _kayit(istemci)

            # Kayıttan hemen sonra: çok sık.
            yanit = await istemci.post("/auth/eposta-dogrulama/yeniden", headers=baslik)
            assert yanit.status_code == 429

            await oturum.execute(
                update(EpostaDogrulama).values(
                    olusturma_tarihi=dt.datetime.now(dt.UTC) - dt.timedelta(minutes=2)
                )
            )
            yanit = await istemci.post("/auth/eposta-dogrulama/yeniden", headers=baslik)
            assert yanit.status_code == 202
            eski, yeni = (_token(e) for e in eposta_gonderilmez.gonderilenler)
            assert eski != yeni
            yanit = await istemci.post("/auth/eposta-dogrula", json={"token": eski})
            assert yanit.status_code == 400
            yanit = await istemci.post("/auth/eposta-dogrula", json={"token": yeni})
            assert yanit.status_code == 200
            hesap_id = (await istemci.get("/me", headers=baslik)).json()["hesap_id"]
            hesap = await oturum.get(Hesap, uuid.UUID(hesap_id))
            assert hesap.eposta_dogrulandi_tarihi is not None

    asyncio.run(senaryo())
