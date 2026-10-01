"""Ad ve kimlik bütünlüğü (docs/plans/dogrulama-iyilestirme.md § 6.3, bulgu 48): saf ad
eşleşmesi ve seviye A koşulu; e-posta doğrulanınca ad kilidi; ad değişikliği talebi
GİRVAK kuyruğuna gider, onay adı uygular ve adla sahipliği kurulmuş kanıtı yeniden açar.

Dünya: test_sahiplik.py — genc1 "Elif", kartı K1, çalışması C1.
"""

import datetime as dt

import pytest
from sqlalchemy import select

from app.agents.dogrulama.kimlik import ad_eslesir, ada_dayali_seviye
from app.core.kanit_okuma.belge import KaynakSeviyesi, SahiplikKaynagi
from app.models.bildirim import TUR_AD_DEGISIKLIGI_SONUCU, Bildirim
from app.models.guven_skoru import GuvenSkoru
from app.models.inceleme_isareti import TUR_AD_DEGISIKLIGI, IncelemeIsareti
from tests.kanit_yardimcisi import link_parcasi
from tests.test_sahiplik import durumlar, senaryo


@pytest.mark.parametrize(
    ("ad", "metin", "beklenen"),
    [
        ("Elif Yılmaz", "Birinci: YILMAZ, ELİF (İTÜ)", True),
        ("Çağrı Öztürk", "cagri ozturk - finalist", True),  # Türkçe karakterden bağımsız
        ("Elif Yılmaz", "Elif Kaya", False),  # bütün parçalar gerekli
        ("Elif", "Elifnur Demir", False),  # parça ayrı kelime olmalı
        ("", "Elif", False),
        ("Elif", None, False),
    ],
)
def test_ad_eslesmesi(ad, metin, beklenen):
    assert ad_eslesir(ad, metin) is beklenen


@pytest.mark.parametrize(
    ("kosullar", "beklenen"),
    [
        ((True, True, True), KaynakSeviyesi.DUZENLEYEN),
        ((True, False, True), KaynakSeviyesi.KAMUYA_ACIK),
        ((True, True, False), KaynakSeviyesi.KAMUYA_ACIK),
        ((False, True, True), KaynakSeviyesi.KAMUYA_ACIK),
    ],
)
def test_ada_dayali_seviye_uc_kosul(kosullar, beklenen):
    ad, eposta, kilit = kosullar
    assert ada_dayali_seviye(ad_eslesti=ad, eposta_dogrulandi=eposta, ad_kilitli_mi=kilit) is (
        beklenen
    )


async def _dogrula(d):
    d.genc1.hesap.eposta_dogrulandi_tarihi = dt.datetime.now(dt.UTC)
    await d.oturum.commit()


def test_dogrulanmamis_hesapta_ad_serbest_talep_409():
    async def adimlar(istemci, d):
        yanit = await istemci.patch("/profil", headers=d.genc1.baslik, json={"ad": "Elif Kaya"})
        assert yanit.status_code == 200
        assert yanit.json()["ad"] == "Elif Kaya"
        assert yanit.json()["ad_kilitli"] is False
        yanit = await istemci.post(
            "/profil/ad-degisikligi", headers=d.genc1.baslik, json={"yeni_ad": "Elif Ak"}
        )
        assert yanit.status_code == 409

    senaryo(adimlar)


def test_kilitli_ad_profilden_degismez_talep_kuyruga_gider():
    async def adimlar(istemci, d):
        await _dogrula(d)
        yanit = await istemci.patch("/profil", headers=d.genc1.baslik, json={"ad": "Elif Kaya"})
        assert yanit.status_code == 409
        assert "kilitli" in yanit.json()["detail"]
        # Yalnızca boşluk ve harf büyüklüğü farkı değişiklik sayılmaz (form adı hep gönderir).
        yanit = await istemci.patch("/profil", headers=d.genc1.baslik, json={"ad": "ELİF"})
        assert yanit.status_code == 200

        yol = "/profil/ad-degisikligi"
        await durumlar(
            istemci, "POST", yol, {None: 401, d.kurum1: 403, d.girvak: 403}, json={"yeni_ad": "X"}
        )
        yanit = await istemci.post(yol, headers=d.genc1.baslik, json={"yeni_ad": "elif"})
        assert yanit.status_code == 422
        yanit = await istemci.post(
            yol, headers=d.genc1.baslik, json={"yeni_ad": " Elif  Kaya ", "gerekce": "Evlilik"}
        )
        assert yanit.status_code == 202
        assert yanit.json()["bekleyen_ad"] == "Elif Kaya"
        assert yanit.json()["ad"] != "Elif Kaya"  # onaya kadar değişmez
        profil = (await istemci.get("/profil", headers=d.genc1.baslik)).json()
        assert profil["ad_kilitli"] is True and profil["bekleyen_ad"] == "Elif Kaya"
        yanit = await istemci.post(yol, headers=d.genc1.baslik, json={"yeni_ad": "Elif Ak"})
        assert yanit.status_code == 409

        isaret = await d.oturum.scalar(
            select(IncelemeIsareti).where(
                IncelemeIsareti.tur == TUR_AD_DEGISIKLIGI,
                IncelemeIsareti.kullanici_id == d.genc1.profil.id,
            )
        )
        assert isaret.ayrinti["yeni_ad"] == "Elif Kaya"
        assert isaret.ayrinti["gerekce"] == "Evlilik"

    senaryo(adimlar)


async def _talep(istemci, d) -> IncelemeIsareti:
    await _dogrula(d)
    yanit = await istemci.post(
        "/profil/ad-degisikligi", headers=d.genc1.baslik, json={"yeni_ad": "Elif Kaya"}
    )
    assert yanit.status_code == 202
    return await d.oturum.scalar(
        select(IncelemeIsareti).where(IncelemeIsareti.kullanici_id == d.genc1.profil.id)
    )


async def _son_bildirim(d) -> str:
    return await d.oturum.scalar(
        select(Bildirim.metin)
        .where(Bildirim.hesap_id == d.genc1.hesap.id, Bildirim.tur == TUR_AD_DEGISIKLIGI_SONUCU)
        .order_by(Bildirim.olusturma_tarihi.desc())
        .limit(1)
    )


def test_onay_adi_uygular_ada_dayali_kaniti_yeniden_acar(kart_hazirlama_arka_plani_yok):
    async def adimlar(istemci, d):
        ad_parcasi = link_parcasi("https://ornek.org/sonuclar")
        ad_parcasi.sahiplik_kaynagi = SahiplikKaynagi.AD.value
        ad_parcasi.somut_cikti_id = d.C1.id
        skor = GuvenSkoru(somut_cikti_id=d.C1.id, degerlendirme_tarihi=dt.datetime.now(dt.UTC))
        d.oturum.add_all([ad_parcasi, skor])
        await d.oturum.commit()

        isaret = await _talep(istemci, d)
        yanit = await istemci.post(
            f"/girvak/inceleme/{isaret.id}/karar",
            headers=d.girvak.baslik,
            json={"karar": "kapandi"},
        )
        assert yanit.status_code == 200
        profil = (await istemci.get("/profil", headers=d.genc1.baslik)).json()
        assert profil["ad"] == "Elif Kaya" and profil["bekleyen_ad"] is None
        assert "onaylandı" in await _son_bildirim(d)

        await d.oturum.refresh(skor)
        assert skor.degerlendirme_tarihi is None  # yeni adla yeniden değerlendirilecek
        assert (d.K1.id, d.K1.versiyon, False) in kart_hazirlama_arka_plani_yok

    senaryo(adimlar)


def test_ret_adi_korur(kart_hazirlama_arka_plani_yok):
    async def adimlar(istemci, d):
        isaret = await _talep(istemci, d)
        yanit = await istemci.post(
            f"/girvak/inceleme/{isaret.id}/karar",
            headers=d.girvak.baslik,
            json={"karar": "dogrulanamadi", "girvak_notu": "Belge gerekli"},
        )
        assert yanit.status_code == 200
        profil = (await istemci.get("/profil", headers=d.genc1.baslik)).json()
        assert profil["ad"] == "Elif"
        metin = await _son_bildirim(d)
        assert "onaylanmadı" in metin and "Belge gerekli" in metin
        assert kart_hazirlama_arka_plani_yok == []

    senaryo(adimlar)
