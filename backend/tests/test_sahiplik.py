"""Sahiplik tablosu (docs/faz-b-kimlik-ve-dongu.md § 3), gerçek token'larla.

Yerel veritabanında, geri alınan bir işlem içinde kurulan dünya:

    genc1 (kart K1, çıktı C1)      genc2 (kart K2)
    kurum1 (ihtiyaç I1)            kurum2 (ihtiyaç I2)
    girvak
    E1: I1 ↔ K1, durum "onerildi"      (kurum1 K1'i görür; genc1 I1'i henüz görmez)
    E2: I2 ↔ K2, durum "ilgileniliyor" (genc2 I2'yi görür)

Hata kodu sözleşmesi: 401 token yok, 403 rol uygun değil, 404 başkasının kaynağı.
LLM ya da embedding çağıran başarı yolları burada sınanmıyor; o uçların
yetkiyi geçip geçmediği, sonrasındaki bilinen hatayla (409 gibi) görülüyor.
"""

import asyncio
import uuid
from types import SimpleNamespace

from sqlalchemy import select

from app.api.auth import hesap_olustur
from app.core.kimlik import token_uret
from app.main import app
from app.models.eslesme import Eslesme
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from tests.veritabani import api_istemcisi, geri_alinan_oturum


class Kisi:
    """Test dünyasındaki bir hesap: token başlığı ve profili. Sözlük anahtarı
    olarak kullanılıyor (kimliğe göre hash'lenir)."""

    def __init__(self, hesap, profil, baslik):
        self.hesap, self.profil, self.baslik = hesap, profil, baslik


async def _hesap(oturum, rol: str, ad: str | None) -> Kisi:
    hesap = await hesap_olustur(
        oturum,
        email=f"test-{uuid.uuid4().hex[:10]}@ornek.com",
        sifre="yeterince-uzun",
        rol=rol,
        ad=ad,
    )
    profil = None
    if rol == "genc":
        profil = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
    elif rol == "kurum":
        profil = await oturum.scalar(select(Kurum).where(Kurum.hesap_id == hesap.id))
    baslik = {"Authorization": f"Bearer {token_uret(hesap.id, rol)}"}
    return Kisi(hesap, profil, baslik)


async def dunya_kur(oturum) -> SimpleNamespace:
    d = SimpleNamespace()
    d.genc1 = await _hesap(oturum, "genc", "Elif")
    d.genc2 = await _hesap(oturum, "genc", "Can")
    d.kurum1 = await _hesap(oturum, "kurum", "Koop Bir")
    d.kurum2 = await _hesap(oturum, "kurum", "Koop İki")
    d.girvak = await _hesap(oturum, "girvak", None)

    d.C1 = SomutCikti(baslik="Kütüphane sistemi")
    d.K1 = YetenekKarti(
        kullanici_id=d.genc1.profil.id,
        rol_alani="backend geliştirici",
        deneyim_seviyesi="orta",
        somut_ciktilar=[d.C1],
    )
    d.K2 = YetenekKarti(
        kullanici_id=d.genc2.profil.id, rol_alani="veri analisti", deneyim_seviyesi="baslangic"
    )
    d.I1 = IhtiyacKarti(kurum_id=d.kurum1.profil.id, problem_tanimi="Ödünç işleri kâğıtla")
    d.I2 = IhtiyacKarti(kurum_id=d.kurum2.profil.id, problem_tanimi="Raporlar elle")
    oturum.add_all([d.K1, d.K2, d.I1, d.I2])
    await oturum.flush()
    d.E1 = Eslesme(ihtiyac_karti_id=d.I1.id, yetenek_karti_id=d.K1.id, skor=0.6, durum="onerildi")
    d.E2 = Eslesme(
        ihtiyac_karti_id=d.I2.id, yetenek_karti_id=d.K2.id, skor=0.5, durum="ilgileniliyor"
    )
    oturum.add_all([d.E1, d.E2])
    await oturum.commit()
    return d


def senaryo(adimlar):
    """Dünyayı kurar, adımları API istemcisiyle çalıştırır, sonunda her şeyi geri alır."""

    async def calistir():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            await adimlar(istemci, await dunya_kur(oturum))

    asyncio.run(calistir())


async def durumlar(istemci, yontem, yol, bekleneler: dict, **govde):
    """Her hesap için durum kodunu kontrol eder. `None` anahtarı = token'sız."""
    for kim, beklenen in bekleneler.items():
        basliklar = kim.baslik if kim is not None else {}
        yanit = await istemci.request(yontem, yol, headers=basliklar, **govde)
        ad = "tokensiz" if kim is None else kim.hesap.rol
        assert yanit.status_code == beklenen, f"{yontem} {yol} [{ad}]: {yanit.status_code}"


# --- Girişsiz uçlar ---------------------------------------------------------------------


def test_saglik_ve_referans_uclari_girissiz():
    async def adimlar(istemci, d):
        assert (await istemci.get("/health")).status_code == 200
        # Bilinmeyen token 404 — 401 değil: uç girişsiz, kimlik token'ın kendisi.
        assert (await istemci.get("/dogrulama/referans/olmayan-token")).status_code == 404
        yanit = await istemci.post(
            "/dogrulama/referans-yaniti", json={"token": "olmayan-token", "puan": 5}
        )
        assert yanit.status_code == 404

    senaryo(adimlar)


# --- Yetenek kartı -------------------------------------------------------------------------


def test_yetenek_karti_gorme():
    """Genç kendi kartını, kurum yalnızca kendisine önerilmiş kartı, GİRVAK hepsini."""

    async def adimlar(istemci, d):
        await durumlar(
            istemci,
            "GET",
            f"/yetenek-kartlari/{d.K1.id}",
            {None: 401, d.genc1: 200, d.genc2: 404, d.kurum1: 200, d.kurum2: 404, d.girvak: 200},
        )

    senaryo(adimlar)


def test_yetenek_karti_embedding_yalnizca_sahibi():
    """Kurum kartı görse de hesaplatamaz; başka genç de. (Sahibin başarı yolu
    Voyage çağırdığı için burada değil.)"""

    async def adimlar(istemci, d):
        await durumlar(
            istemci,
            "POST",
            f"/yetenek-kartlari/{d.K1.id}/embedding",
            {None: 401, d.genc2: 404, d.kurum1: 404},
        )

    senaryo(adimlar)


# --- İhtiyaç kartı -------------------------------------------------------------------------


def test_ihtiyac_karti_gorme():
    """Genç ihtiyacı ancak kurum ilgilendikten sonra görür."""

    async def adimlar(istemci, d):
        await durumlar(
            istemci,
            "GET",
            f"/ihtiyac-kartlari/{d.I1.id}",
            # E1 hâlâ "onerildi": genc1 I1'i görmez
            {None: 401, d.kurum1: 200, d.kurum2: 404, d.genc1: 404, d.girvak: 200},
        )
        await durumlar(
            istemci,
            "GET",
            f"/ihtiyac-kartlari/{d.I2.id}",
            # E2 "ilgileniliyor": genc2 I2'yi görür, genc1 görmez
            {d.genc2: 200, d.genc1: 404},
        )

    senaryo(adimlar)


def test_ihtiyac_karti_embedding_yalnizca_sahibi():
    async def adimlar(istemci, d):
        await durumlar(
            istemci,
            "POST",
            f"/ihtiyac-kartlari/{d.I1.id}/embedding",
            {None: 401, d.kurum2: 404, d.genc1: 404},
        )

    senaryo(adimlar)


# --- Eşleştirme ------------------------------------------------------------------------------


def test_eslestirme_calistir():
    """Kurum yalnızca kendi kurumu için; GİRVAK hangi kurum olduğunu söylemeli.
    Yetkiyi geçen istek, I1'in embedding'i olmadığı için 409'a düşüyor."""

    async def adimlar(istemci, d):
        await durumlar(istemci, "POST", "/eslestirme/calistir", {None: 401, d.genc1: 403}, json={})
        await durumlar(
            istemci,
            "POST",
            "/eslestirme/calistir",
            {d.kurum1: 404},
            json={"kurum_id": str(d.kurum2.profil.id)},
        )
        await durumlar(istemci, "POST", "/eslestirme/calistir", {d.kurum1: 409}, json={})
        await durumlar(istemci, "POST", "/eslestirme/calistir", {d.girvak: 422}, json={})
        await durumlar(
            istemci,
            "POST",
            "/eslestirme/calistir",
            {d.girvak: 409},
            json={"kurum_id": str(d.kurum1.profil.id)},
        )

    senaryo(adimlar)


def test_oneriler_yalnizca_kendi_kurumu():
    async def adimlar(istemci, d):
        await durumlar(
            istemci,
            "GET",
            f"/eslestirme/oneriler/{d.kurum1.profil.id}",
            {None: 401, d.genc1: 403, d.kurum2: 404, d.kurum1: 200, d.girvak: 200},
        )

    senaryo(adimlar)


def test_ilgileniyorum_yalnizca_ihtiyacin_sahibi_kurum():
    async def adimlar(istemci, d):
        govde = {"json": {"eslesme_id": str(d.E1.id)}}
        await durumlar(
            istemci,
            "POST",
            "/eslestirme/ilgileniyorum",
            {None: 401, d.genc1: 403, d.girvak: 403, d.kurum2: 404},
            **govde,
        )
        await durumlar(istemci, "POST", "/eslestirme/ilgileniyorum", {d.kurum1: 200}, **govde)

    senaryo(adimlar)


# --- Doğrulama ------------------------------------------------------------------------------


def test_kanit_durumu_yalnizca_sahibi_ve_girvak():
    """Kurum 403: referans e-postaları ve yanıt linkleri kuruma hiç gitmez."""

    async def adimlar(istemci, d):
        await durumlar(
            istemci,
            "GET",
            f"/dogrulama/kanit/{d.C1.id}",
            {None: 401, d.genc1: 200, d.genc2: 404, d.kurum1: 403, d.girvak: 200},
        )

    senaryo(adimlar)


def test_kanit_ekle_ve_itiraz_yalnizca_sahibi():
    """Başarı yolu link kontrolü ve LLM çağırdığı için burada değil."""

    async def adimlar(istemci, d):
        for yol in ("/dogrulama/kanit-ekle", "/dogrulama/itiraz"):
            await durumlar(
                istemci,
                "POST",
                yol,
                {None: 401, d.kurum1: 403, d.girvak: 403, d.genc2: 404},
                json={"somut_cikti_id": str(d.C1.id), "kanit_linki": "https://ornek.com"},
            )

    senaryo(adimlar)


# --- Sohbetler -------------------------------------------------------------------------------


class SahipliGrafik:
    """Checkpoint'te sahibi belli bir sohbet; ainvoke gelen girdiyi sahibiyle döner."""

    def __init__(self, sahip_hesap_id):
        self.sahip = str(sahip_hesap_id)

    async def aget_state(self, _config):
        return SimpleNamespace(values={"sahip_hesap_id": self.sahip, "taslak": {}})

    async def ainvoke(self, girdi, config=None):
        return {"taslak": {}, "sonraki_soru": "Devam?", "taslak_hazir": False, **girdi}


def test_sohbetleri_yalnizca_rolun_sahibi_surdurur():
    async def adimlar(istemci, d):
        app.state.kesif_grafigi = SahipliGrafik(d.genc1.hesap.id)
        app.state.tanimlama_grafigi = SahipliGrafik(d.kurum1.hesap.id)
        try:
            await durumlar(
                istemci, "POST", "/kesif/sohbet/baslat", {None: 401, d.kurum1: 403}, json={}
            )
            await durumlar(
                istemci, "POST", "/tanimlama/sohbet/baslat", {None: 401, d.genc1: 403}, json={}
            )

            cevap = {"json": {"oturum_id": str(uuid.uuid4()), "cevap": "merhaba"}}
            await durumlar(
                istemci,
                "POST",
                "/kesif/sohbet/cevap",
                {d.genc2: 404, d.kurum1: 403, d.genc1: 200},
                **cevap,
            )
            await durumlar(
                istemci,
                "POST",
                "/tanimlama/sohbet/cevap",
                {d.kurum2: 404, d.genc1: 403, d.kurum1: 200},
                **cevap,
            )
            onay = {
                "json": {
                    "oturum_id": str(uuid.uuid4()),
                    "profil": {"sehir": "İzmir"},
                }
            }
            await durumlar(istemci, "POST", "/kesif/kart/onayla", {d.genc2: 404}, **onay)
        finally:
            del app.state.kesif_grafigi
            del app.state.tanimlama_grafigi

    senaryo(adimlar)


def test_yeni_sohbet_acanin_kimligini_checkpointe_yazar():
    async def adimlar(istemci, d):
        girdiler = []

        class KaydedenGrafik(SahipliGrafik):
            async def ainvoke(self, girdi, config=None):
                girdiler.append(girdi)
                return await super().ainvoke(girdi, config)

        app.state.kesif_grafigi = KaydedenGrafik(d.genc1.hesap.id)
        try:
            yanit = await istemci.post("/kesif/sohbet/baslat", json={}, headers=d.genc1.baslik)
        finally:
            del app.state.kesif_grafigi
        assert yanit.status_code == 200
        assert girdiler == [{"sahip_hesap_id": str(d.genc1.hesap.id)}]

    senaryo(adimlar)
