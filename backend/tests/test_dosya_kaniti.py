"""Dosya ve görsel kanıtı uçları (plan § 4): yükleme, tekrar, sınırlar, indirme adresi,
görünürlük, silme ve sahiplik üçlüsü (401 / 403 / 404)."""

import asyncio
import uuid

import pytest

from app.api.auth import hesap_olustur
from app.core.dis_servisler import kurulum
from app.core.dis_servisler.depo import KapaliDepo
from app.core.kimlik import token_uret
from app.models.yetenek_karti import YetenekKarti
from app.servisler.dogrulama import parcalar
from tests import dosya_ornekleri as ornek
from tests.test_kanit_parcasi import _genc_ve_kalem, _kalemi_oku, sahte_degerlendirme  # noqa: F401
from tests.veritabani import api_istemcisi, geri_alinan_oturum

# Okuma ve model çıkarımı sahte (test_kanit_parcasi fixture).
pytestmark = pytest.mark.usefixtures("sahte_degerlendirme")


def _yukle(istemci, kalem_id, baslik, ham, ad="rapor.pdf"):
    return istemci.post(
        f"/dogrulama/kalem/{kalem_id}/dosya", headers=baslik, files={"dosya": (ad, ham)}
    )


def test_pdf_yuklenir_depoya_konur_ve_parca_olur(depo):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(oturum)
            yanit = await _yukle(istemci, kalem_id, baslik, ornek.pdf(javascript=True))
            assert yanit.status_code == 201, yanit.text
            [kanit] = yanit.json()["kanitlar"]
            assert kanit["tur"] == "dosya"
            assert kanit["dosya_adi"] == "rapor.pdf"
            assert kanit["gorunur_firmaya"] is False
            kalem = await _kalemi_oku(oturum, kalem_id)
            parca = kalem.kanit_parcalari[0]
            assert parca.dosya_anahtari.startswith("kanit/")
            assert parca.belge["dosya"]["tarama"] == "taranmadi"
            assert b"JavaScript" not in await depo.al(parca.dosya_anahtari)

            # Aynı dosya ikinci kez: 409
            tekrar = await _yukle(istemci, kalem_id, baslik, ornek.pdf(javascript=True))
            assert tekrar.status_code == 409, tekrar.text

    asyncio.run(senaryo())


def test_desteklenmeyen_dosya_422_ve_depoya_bir_sey_konmaz(depo):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(oturum)
            yanit = await _yukle(istemci, kalem_id, baslik, b"<html></html>", ad="x.pdf")
            assert yanit.status_code == 422
            assert "Yalnızca PDF" in yanit.json()["detail"]
            assert not list(depo.yol("kanit/00000000").parent.parent.glob("**/*.*"))

    asyncio.run(senaryo())


def test_kalem_basina_dosya_siniri(monkeypatch):
    monkeypatch.setattr(parcalar, "KALEM_BASINA_DOSYA", 1)

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(oturum)
            assert (await _yukle(istemci, kalem_id, baslik, ornek.pdf())).status_code == 201
            ikinci = await _yukle(istemci, kalem_id, baslik, ornek.gorsel(), ad="a.png")
            assert ikinci.status_code == 422
            assert "en çok 1 dosya" in ikinci.json()["detail"]

    asyncio.run(senaryo())


def test_depo_kapaliysa_503(monkeypatch):
    monkeypatch.setattr(kurulum, "depo", lambda: KapaliDepo())

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(oturum)
            yanit = await _yukle(istemci, kalem_id, baslik, ornek.pdf())
            assert yanit.status_code == 503
            assert (await _kalemi_oku(oturum, kalem_id)).kanit_parcalari == []

    asyncio.run(senaryo())


def test_indirme_adresi_gorunurluk_ve_silme(depo):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(oturum)
            yanit = await _yukle(istemci, kalem_id, baslik, ornek.gorsel("PNG"), ad="ekran.png")
            parca_id = yanit.json()["kanitlar"][0]["id"]
            adres = await istemci.get(
                f"/dogrulama/kalem/{kalem_id}/kanit/{parca_id}/indir", headers=baslik
            )
            assert adres.status_code == 200
            indirme = await istemci.get(adres.json()["adres"].replace("http://testserver", ""))
            assert indirme.status_code == 200
            assert indirme.headers["content-disposition"].startswith("attachment")

            acik = await istemci.patch(
                f"/dogrulama/kalem/{kalem_id}/kanit/{parca_id}",
                headers=baslik,
                json={"gorunur_firmaya": True},
            )
            assert acik.json()["kanitlar"][0]["gorunur_firmaya"] is True

            anahtar = (await _kalemi_oku(oturum, kalem_id)).kanit_parcalari[0].dosya_anahtari
            sil = await istemci.delete(
                f"/dogrulama/kalem/{kalem_id}/kanit/{parca_id}", headers=baslik
            )
            assert sil.status_code == 200
            assert not depo.yol(anahtar).exists()

    asyncio.run(senaryo())


def test_kalem_silinince_dosyasi_da_silinir(depo):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, kart_id, kalem_id = await _genc_ve_kalem(oturum)
            await _yukle(istemci, kalem_id, baslik, ornek.pdf())
            anahtar = (await _kalemi_oku(oturum, kalem_id)).kanit_parcalari[0].dosya_anahtari
            # Kartın iki kalemi olsun: son kalem silinemiyor olabilir.
            await istemci.post(
                f"/yetenek-kartlari/{kart_id}/ciktilar",
                headers=baslik,
                json={"baslik": "İkinci çalışma"},
            )
            sil = await istemci.delete(
                f"/yetenek-kartlari/{kart_id}/ciktilar/{kalem_id}", headers=baslik
            )
            assert sil.status_code == 200, sil.text
            assert not depo.yol(anahtar).exists()

    asyncio.run(senaryo())


def test_sahiplik_401_403_404():
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(oturum)
            yanit = await _yukle(istemci, kalem_id, baslik, ornek.pdf())
            parca_id = yanit.json()["kanitlar"][0]["id"]
            indir = f"/dogrulama/kalem/{kalem_id}/kanit/{parca_id}/indir"

            assert (await istemci.get(indir)).status_code == 401
            kurum = await hesap_olustur(
                oturum,
                email=f"k-{uuid.uuid4().hex[:8]}@ornek.com",
                sifre="yeterince-uzun",
                rol="kurum",
                ad="Firma",
            )
            kurum_basligi = {"Authorization": f"Bearer {token_uret(kurum.id, kurum.rol)}"}
            assert (await istemci.get(indir, headers=kurum_basligi)).status_code == 403
            assert (await _yukle(istemci, kalem_id, kurum_basligi, b"x")).status_code == 403

            baska, _, _ = await _genc_ve_kalem(oturum)
            assert (await istemci.get(indir, headers=baska)).status_code == 404
            assert (await _yukle(istemci, kalem_id, baska, ornek.pdf())).status_code == 404
            yok = f"/dogrulama/kalem/{kalem_id}/kanit/{uuid.uuid4()}/indir"
            assert (await istemci.get(yok, headers=baslik)).status_code == 404

    asyncio.run(senaryo())


def test_qr_ile_dogrulanan_belge_duzenleyen_seviyesinde(monkeypatch):
    """QR bilinen düzenleyene gidiyor, sayfada gencin adı var, e-posta doğrulanmış
    (ad kilitli): seviye A, Kanıt 3. E-posta doğrulanmamışken aynı belge C (Kanıt 2)."""
    import datetime as dt

    from sqlalchemy import select

    from app.models.hesap import Hesap
    from app.models.kullanici import Kullanici
    from app.servisler.dogrulama.capalar import adres
    from tests.test_capalar import _qr_png

    async def sayfa(_adres, _transport):
        return "Python Temelleri Sertifikası Elif"

    monkeypatch.setattr(adres, "sayfa_metni", sayfa)

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, kart_id, kalem_id = await _genc_ve_kalem(oturum)
            qr = _qr_png("https://www.credly.com/badges/abc-123")
            yanit = await _yukle(istemci, kalem_id, baslik, qr, ad="rozet.png")
            assert yanit.status_code == 201, yanit.text
            assert yanit.json()["kanitlar"][0]["seviye"] == "kamuya_acik"
            assert yanit.json()["guven_skoru"]["kanit_orijinalligi"] == 2

            kart = await oturum.get(YetenekKarti, kart_id)
            kullanici = await oturum.get(Kullanici, kart.kullanici_id)
            hesap = await oturum.scalar(select(Hesap).where(Hesap.id == kullanici.hesap_id))
            hesap.eposta_dogrulandi_tarihi = dt.datetime.now(dt.UTC)
            await oturum.commit()
            yeniden = await istemci.post(f"/dogrulama/kalem/{kalem_id}/degerlendir", headers=baslik)
            assert yeniden.status_code == 200, yeniden.text
            assert yeniden.json()["kanitlar"][0]["seviye"] == "duzenleyen"
            assert yeniden.json()["guven_skoru"]["kanit_orijinalligi"] == 3
            kalem = await _kalemi_oku(oturum, kalem_id)
            [capa] = kalem.kanit_parcalari[0].belge["capalar"]
            assert capa["duzenleyen"] == "Credly" and capa["ad_eslesti"] is True
            assert kalem.kanit_parcalari[0].sahiplik_kaynagi == "ad"

    asyncio.run(senaryo())


def test_eposta_dogrulaninca_dosyasi_olan_kart_yeniden_okunur():
    from sqlalchemy import select

    from app.models.hesap import Hesap
    from app.models.kullanici import Kullanici
    from app.servisler import kimlik_dogrulama

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, kart_id, kalem_id = await _genc_ve_kalem(oturum)
            kart = await oturum.get(YetenekKarti, kart_id)
            kullanici = await oturum.get(Kullanici, kart.kullanici_id)
            hesap = await oturum.scalar(select(Hesap).where(Hesap.id == kullanici.hesap_id))
            assert await kimlik_dogrulama.dogrulama_sonrasi_kart(oturum, hesap) is None
            await _yukle(istemci, kalem_id, baslik, ornek.pdf())
            assert await kimlik_dogrulama.dogrulama_sonrasi_kart(oturum, hesap) == kart_id

    asyncio.run(senaryo())
