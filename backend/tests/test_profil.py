"""Onay hesaba bağlı; profil güncellemesi boş gelenle eskisini silmez.

Faz B'den önce onay e-postayla profili bulup oluşturuyordu (upsert). Artık
kart token'daki hesabın profiline bağlanıyor, onay yalnızca eşleştirmeyi
etkileyen alanları güncelliyor (docs/faz-b-kimlik-ve-dongu.md § 4). Hesabı
olmayan profilin kartı eşleştirmeye girmiyor (§ 8).
"""

import asyncio
import uuid
from types import SimpleNamespace

from sqlalchemy import select

from app.agents.eslestirme import adaylari_getir
from app.api import ihtiyac_kartlari as ihtiyac_api
from app.api import tanimlama as tanimlama_api
from app.api import yetenek_kartlari as yetenek_api
from app.api.auth import hesap_olustur
from app.api.kesif import SEHIR_GEREKLI
from app.api.profil import gencin_profilini_guncelle, kurumun_profilini_guncelle
from app.core.kimlik import token_uret
from app.core.metin import eposta_normalize
from app.db.base import EMBEDDING_DIM
from app.main import app
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.models.yetenek_karti import YetenekKarti
from app.schemas.kesif import GencProfili
from app.schemas.tanimlama import KurumProfili
from tests.veritabani import api_istemcisi, geri_alinan_oturum

VEKTOR = [1.0] + [0.0] * (EMBEDDING_DIM - 1)

# --- E-posta: artık iletişim bilgisi, yine tekil -------------------------------------


def test_eposta_alanlari_tekil():
    assert Kullanici.__table__.c.email.unique is True
    assert Kurum.__table__.c.iletisim_email.unique is True


def test_eposta_normalize_edilir():
    assert eposta_normalize("  Elif@Ornek.COM ") == "elif@ornek.com"


# --- Profil güncellemesi (saf) -------------------------------------------------------------


def _genc():
    return SimpleNamespace(sehir="İzmir", calisma_modelleri=["hibrit"], musaitlik="staj")


def test_bos_gelen_alan_kayitli_degeri_silmez():
    kullanici = _genc()
    gencin_profilini_guncelle(kullanici, GencProfili())
    assert (kullanici.sehir, kullanici.calisma_modelleri, kullanici.musaitlik) == (
        "İzmir",
        ["hibrit"],
        "staj",
    )


def test_dolu_gelen_alan_gunceller_ve_kanoniklesir():
    kullanici = _genc()
    gencin_profilini_guncelle(
        kullanici,
        GencProfili(
            sehir="istanbul", calisma_modelleri=["uzaktan", "evden"], musaitlik="Tam zamanlı"
        ),
    )
    assert kullanici.sehir == "İstanbul"
    assert kullanici.calisma_modelleri == ["uzaktan"]  # tanınmayan atıldı
    assert kullanici.musaitlik == "tam_zamanli"


def test_kurum_profili_bos_sektorle_silinmez():
    kurum = SimpleNamespace(sektor="kamu", sehir="Ankara")
    kurumun_profilini_guncelle(kurum, KurumProfili(sektor="  ", sehir=None))
    assert (kurum.sektor, kurum.sehir) == ("kamu", "Ankara")
    kurumun_profilini_guncelle(kurum, KurumProfili(sektor="eğitim", sehir="izmir"))
    assert (kurum.sektor, kurum.sehir) == ("eğitim", "İzmir")


# --- Onay hesaba bağlanıyor (gerçek veritabanında) ---------------------------------------


class HazirTaslakGrafigi:
    """Sahibi belli, taslağı hazır bir sohbet."""

    def __init__(self, sahip_hesap_id, taslak):
        self.sahip, self.taslak = str(sahip_hesap_id), taslak

    async def aget_state(self, _config):
        return SimpleNamespace(
            values={"sahip_hesap_id": self.sahip, "taslak_hazir": True, "taslak": self.taslak}
        )


YETENEK_TASLAGI = {
    "rol_alani": "backend geliştirici",
    "deneyim_seviyesi": "orta",
    "sektor_ilgi_alani": ["eğitim"],
    "araclar_teknolojiler": ["Python"],
    "somut_ciktilar": [{"baslik": "Kütüphane sistemi"}],
}


def _embedding_sahte(monkeypatch):
    async def uret(_metin, girdi_turu="document"):
        return VEKTOR

    monkeypatch.setattr(yetenek_api, "embedding_uret", uret)
    monkeypatch.setattr(ihtiyac_api, "embedding_uret", uret)


def test_yetenek_karti_hesabin_profiline_baglanir_ve_profil_bosla_silinmez(monkeypatch):
    _embedding_sahte(monkeypatch)

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap = await hesap_olustur(
                oturum,
                email=f"test-{uuid.uuid4().hex[:8]}@ornek.com",
                sifre="yeterince-uzun",
                rol="genc",
                ad="Elif",
            )
            baslik = {"Authorization": f"Bearer {token_uret(hesap.id, 'genc')}"}
            app.state.kesif_grafigi = HazirTaslakGrafigi(hesap.id, YETENEK_TASLAGI)
            try:
                ilk = await istemci.post(
                    "/kesif/kart/onayla",
                    headers=baslik,
                    json={
                        "oturum_id": str(uuid.uuid4()),
                        "profil": {
                            "sehir": "izmir",
                            "calisma_modelleri": ["hibrit"],
                            "musaitlik": "yarim_zamanli",
                        },
                    },
                )
                # İkinci kart: profil alanları gönderilmedi, eskisi kalmalı
                ikinci = await istemci.post(
                    "/kesif/kart/onayla",
                    headers=baslik,
                    json={"oturum_id": str(uuid.uuid4()), "profil": {}},
                )
            finally:
                del app.state.kesif_grafigi

            assert ilk.status_code == ikinci.status_code == 201
            profil = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
            await oturum.refresh(profil)
            assert (profil.sehir, profil.calisma_modelleri, profil.musaitlik) == (
                "İzmir",
                ["hibrit"],
                "yarim_zamanli",
            )
            assert profil.email == hesap.email  # iletişim e-postası kayıttaki
            kartlar = (
                await oturum.scalars(
                    select(YetenekKarti.id).where(YetenekKarti.kullanici_id == profil.id)
                )
            ).all()
            assert {str(k) for k in kartlar} == {ilk.json()["id"], ikinci.json()["id"]}

    asyncio.run(senaryo())


def test_sehri_olmayan_profille_onay_422():
    """İlk kartta şehir verilmediyse kart açılmaz: eşleştirme şehre göre süzüyor."""

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap = await hesap_olustur(
                oturum,
                email=f"test-{uuid.uuid4().hex[:8]}@ornek.com",
                sifre="yeterince-uzun",
                rol="genc",
                ad="Can",
            )
            app.state.kesif_grafigi = HazirTaslakGrafigi(hesap.id, YETENEK_TASLAGI)
            try:
                yanit = await istemci.post(
                    "/kesif/kart/onayla",
                    headers={"Authorization": f"Bearer {token_uret(hesap.id, 'genc')}"},
                    json={"oturum_id": str(uuid.uuid4()), "profil": {}},
                )
            finally:
                del app.state.kesif_grafigi
            assert yanit.status_code == 422
            assert yanit.json()["detail"] == SEHIR_GEREKLI

    asyncio.run(senaryo())


def test_ihtiyac_karti_hesabin_kurumuna_baglanir(monkeypatch):
    _embedding_sahte(monkeypatch)

    async def eslestirme_yok(_kurum_id):
        pass

    monkeypatch.setattr(tanimlama_api, "eslestirmeyi_arka_planda_calistir", eslestirme_yok)

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap = await hesap_olustur(
                oturum,
                email=f"test-{uuid.uuid4().hex[:8]}@koop.org",
                sifre="yeterince-uzun",
                rol="kurum",
                ad="Koop",
            )
            baslik = {"Authorization": f"Bearer {token_uret(hesap.id, 'kurum')}"}
            taslak = {"problem_tanimi": "Ödünç kâğıtla", "basari_kriteri": "%100 dijital"}
            app.state.tanimlama_grafigi = HazirTaslakGrafigi(hesap.id, taslak)
            try:
                yanit = await istemci.post(
                    "/tanimlama/kart/onayla",
                    headers=baslik,
                    json={"oturum_id": str(uuid.uuid4()), "kurum_profili": {"sektor": "kamu"}},
                )
                await istemci.post(
                    "/tanimlama/kart/onayla",
                    headers=baslik,
                    json={"oturum_id": str(uuid.uuid4()), "kurum_profili": {}},
                )
            finally:
                del app.state.tanimlama_grafigi

            assert yanit.status_code == 201
            kurum = await oturum.scalar(select(Kurum).where(Kurum.hesap_id == hesap.id))
            await oturum.refresh(kurum)
            assert yanit.json()["kurum"]["id"] == str(kurum.id)
            assert kurum.sektor == "kamu"  # ikinci onay boş gönderdi, silinmedi
            assert kurum.ad == "Koop"

    asyncio.run(senaryo())


# --- Hesapsız profilin kartı eşleştirmeye girmez (§ 8) -----------------------------------


def test_hesapsiz_profilin_karti_aday_olmaz():
    """İki kart ihtiyaçla birebir aynı vektörde; yalnızca hesabı olan aday çıkar."""

    async def senaryo():
        async with geri_alinan_oturum() as oturum:
            hesap = await hesap_olustur(
                oturum,
                email=f"test-{uuid.uuid4().hex[:8]}@ornek.com",
                sifre="yeterince-uzun",
                rol="genc",
                ad="Hesaplı",
            )
            hesapli = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
            hesapsiz = Kullanici(ad="Eski", email=f"test-{uuid.uuid4().hex[:8]}@ornek.com")
            kurum = Kurum(ad="Koop")
            oturum.add_all([hesapsiz, kurum])
            await oturum.flush()

            ortak = {"rol_alani": "r", "deneyim_seviyesi": "orta", "embedding": VEKTOR}
            k_hesapli = YetenekKarti(kullanici_id=hesapli.id, **ortak)
            k_hesapsiz = YetenekKarti(kullanici_id=hesapsiz.id, **ortak)
            ihtiyac = IhtiyacKarti(kurum_id=kurum.id, problem_tanimi="p", embedding=VEKTOR)
            oturum.add_all([k_hesapli, k_hesapsiz, ihtiyac])
            await oturum.flush()

            adaylar = {a.yetenek_karti.id for a in await adaylari_getir(oturum, ihtiyac)}
            assert k_hesapli.id in adaylar
            assert k_hesapsiz.id not in adaylar

    asyncio.run(senaryo())
