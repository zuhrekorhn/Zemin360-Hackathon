"""Canlılık taraması (docs/faz-d-canlilik.md § 1-4), gerçek veritabanında.

Dünya: test_sahiplik.py — E1 = I1 (kurum1 "Koop Bir") ↔ K1 (genc1 "Elif"),
`onerildi`; E2 = I2 (kurum2 "Koop İki") ↔ K2 (genc2 "Can"), `ilgileniliyor`.
Tarama bütün veritabanını tarar (geri alınan işlem içinde); doğrulamalar
yalnızca bu dünyanın kayıtlarına bakar.
"""

import datetime as dt

import pytest
from sqlalchemy import select

from app.api import canlilik as canlilik_api
from app.core.config import get_settings
from app.models.canlilik_olayi import CanlilikOlayi
from app.models.eslesme import Eslesme
from app.models.kullanici import Kullanici
from app.models.yetenek_karti import YetenekKarti
from tests.takip_dunyasi import bildirimleri, isbirligi_ac
from tests.test_sahiplik import durumlar, senaryo
from tests.test_takip_isaret import aktif_isbirligi

SIMDI = lambda: dt.datetime.now(dt.UTC)  # noqa: E731


async def _gecmise(d, eslesme, gun):
    eslesme.son_aktivite_tarihi = SIMDI() - dt.timedelta(days=gun)
    await d.oturum.commit()


async def _olaylar(d, *eslesmeler):
    return list(
        await d.oturum.scalars(
            select(CanlilikOlayi)
            .where(CanlilikOlayi.eslesme_id.in_([e.id for e in eslesmeler]))
            .order_by(CanlilikOlayi.tetiklenme_tarihi)
        )
    )


async def _tara(d):
    return await canlilik_api.tarama_yap(d.oturum)


def test_bakilmayan_oneriler_kuruma_tek_toplu_bildirim_ve_idempotent():
    async def adimlar(istemci, d):
        ikinci = Eslesme(
            ihtiyac_karti_id=d.I1.id, yetenek_karti_id=d.K2.id, skor=0.5, durum="onerildi"
        )
        d.oturum.add(ikinci)
        await d.oturum.flush()
        await _gecmise(d, d.E1, 8)
        await _gecmise(d, ikinci, 10)

        await _tara(d)
        olaylar = await _olaylar(d, d.E1, ikinci)
        assert sorted(o.tur for o in olaylar) == ["oneri_bekliyor", "oneri_bekliyor"]
        assert {o.alici_hesap_id for o in olaylar} == {d.kurum1.hesap.id}
        kuruma = await bildirimleri(d, d.kurum1)
        assert [b.tur for b in kuruma] == ["oneri_bekliyor"]  # iki öneri, TEK bildirim
        assert "2 öneri 10 gündür" in kuruma[0].metin

        # Art arda ikinci tarama: bu dönemde zaten hatırlatıldı, hiçbir şey yazılmaz.
        await _tara(d)
        assert len(await _olaylar(d, d.E1, ikinci)) == 2
        assert len(await bildirimleri(d, d.kurum1)) == 1

    senaryo(adimlar)


def test_hareket_donemi_kapatir_yeniden_susunca_yeni_hatirlatma():
    async def adimlar(istemci, d):
        await _gecmise(d, d.E1, 8)
        await _tara(d)
        [olay] = await _olaylar(d, d.E1)
        # Olaydan SONRA biri hareket etti, sonra yine 8 gün sustu: yeni dönem.
        olay.tetiklenme_tarihi = SIMDI() - dt.timedelta(days=20)
        await _gecmise(d, d.E1, 8)
        await _tara(d)
        assert len(await _olaylar(d, d.E1)) == 2

    senaryo(adimlar)


def test_yanitsiz_ilgi_iki_kademe():
    async def adimlar(istemci, d):
        await _gecmise(d, d.E2, 4)
        await _tara(d)
        assert [(o.tur, o.alici_hesap_id) for o in await _olaylar(d, d.E2)] == [
            ("ilgi_yanitsiz_1", d.genc2.hesap.id)
        ]
        assert "Koop İki 4 gündür yanıtını bekliyor" in (await bildirimleri(d, d.genc2))[0].metin

        await _tara(d)  # tekrar yok
        assert len(await _olaylar(d, d.E2)) == 1

        await _gecmise(d, d.E2, 11)
        await _tara(d)
        ikinci = [(o.tur, o.alici_hesap_id) for o in (await _olaylar(d, d.E2))[1:]]
        assert sorted(ikinci, key=str) == sorted(
            [("ilgi_yanitsiz_2", d.genc2.hesap.id), ("ilgi_yanitsiz_2", d.kurum2.hesap.id)],
            key=str,
        )
        assert "son hatırlatma" in (await bildirimleri(d, d.genc2))[-1].metin
        assert "Can 11 gündür yanıt vermedi" in (await bildirimleri(d, d.kurum2))[-1].metin

    senaryo(adimlar)


def test_onaylanmayan_plan_yalnizca_onaylamayana():
    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d, adimlar=1)
        isb.genc_plan_onayi = SIMDI()
        await _gecmise(d, d.E1, 6)
        await _tara(d)
        assert [(o.tur, o.alici_hesap_id) for o in await _olaylar(d, d.E1)] == [
            ("plan_onaysiz", d.kurum1.hesap.id)
        ]
        assert (
            "Elif ile planınız 6 gündür onay bekliyor"
            in (await bildirimleri(d, d.kurum1))[-1].metin
        )

    senaryo(adimlar)


def test_gecikmis_adim_ve_hareketsizlik_onceligi():
    async def adimlar(istemci, d):
        isb = await aktif_isbirligi(d, adimlar=2)
        birinci = sorted(isb.milestonelar, key=lambda m: m.sira)[0]
        birinci.hedef_tarih = dt.date.today() - dt.timedelta(days=3)
        birinci.genc_isaret = SIMDI()  # genç tamamlandı dedi, kurum demedi
        await _gecmise(d, d.E1, 20)

        await _tara(d)
        olaylar = {(o.tur, o.alici_hesap_id, o.milestone_id) for o in await _olaylar(d, d.E1)}
        assert olaylar == {
            ("adim_gecikti", d.kurum1.hesap.id, birinci.id),
            # Kurum gecikmeden haberdar; ona ayrıca "hareket yok" gitmez.
            ("isbirligi_hareketsiz", d.genc1.hesap.id, None),
        }
        assert (
            "“Adım 1” adımının hedef tarihi 3 gün geçti"
            in (await bildirimleri(d, d.kurum1))[-1].metin
        )

    senaryo(adimlar)


def test_tarama_hareket_sayilmaz_ve_hesapsiz_profil_atlanir():
    async def adimlar(istemci, d):
        hesapsiz = Kullanici(ad="Eski", email="eski-profil@ornek.com")
        d.oturum.add(hesapsiz)
        await d.oturum.flush()
        kart = YetenekKarti(kullanici_id=hesapsiz.id, rol_alani="r", deneyim_seviyesi="orta")
        d.oturum.add(kart)
        await d.oturum.flush()
        eski = Eslesme(
            ihtiyac_karti_id=d.I2.id, yetenek_karti_id=kart.id, skor=0.5, durum="ilgileniliyor"
        )
        d.oturum.add(eski)
        await d.oturum.flush()
        await _gecmise(d, eski, 5)
        await _gecmise(d, d.E1, 8)
        once = d.E1.son_aktivite_tarihi

        await _tara(d)
        assert await _olaylar(d, eski) == []  # okuyacak kimse yok
        await d.oturum.refresh(d.E1)
        assert d.E1.son_aktivite_tarihi == once  # hatırlatma hareket değil

    senaryo(adimlar)


# --- Yetki: GİRVAK token'ı ya da cron anahtarı ---------------------------------------------

ANAHTAR = "cron-icin-yeterince-uzun-gizli-anahtar-0123456789"


def test_girvak_tokeni_ile_tarama():
    async def adimlar(istemci, d):
        await durumlar(
            istemci,
            "POST",
            "/canlilik/tarama",
            {None: 401, d.genc1: 403, d.kurum1: 403, d.girvak: 200},
        )
        yanit = await istemci.post("/canlilik/tarama", headers=d.girvak.baslik)
        assert set(yanit.json()) == {"tarih", "olaylar", "bildirim", "sure_sn"}

    senaryo(adimlar)


def test_anahtar_tanimli_degilse_baslik_yolu_kapali(monkeypatch):
    monkeypatch.setattr(get_settings(), "tarama_anahtari", "")

    async def adimlar(istemci, d):
        yanit = await istemci.post("/canlilik/tarama", headers={"X-Tarama-Anahtari": ANAHTAR})
        assert yanit.status_code == 401
        assert yanit.json()["detail"] == canlilik_api.ANAHTAR_TANIMSIZ

    senaryo(adimlar)


def test_cron_anahtari_kullanici_tokeni_olmadan_calisir(monkeypatch):
    monkeypatch.setattr(get_settings(), "tarama_anahtari", ANAHTAR)

    async def adimlar(istemci, d):
        dogru = await istemci.post("/canlilik/tarama", headers={"X-Tarama-Anahtari": ANAHTAR})
        assert dogru.status_code == 200
        yanlis = await istemci.post(
            "/canlilik/tarama", headers={"X-Tarama-Anahtari": ANAHTAR + "x"}
        )
        assert yanlis.status_code == 401
        assert yanlis.json()["detail"] == canlilik_api.ANAHTAR_GECERSIZ
        # Başlık varken token'a bakılmaz: GİRVAK token'ı yanlış anahtarı kurtarmaz.
        karisik = await istemci.post(
            "/canlilik/tarama",
            headers={"X-Tarama-Anahtari": "yanlis", **d.girvak.baslik},
        )
        assert karisik.status_code == 401
        # Anahtar tanımlıyken GİRVAK token'ı yolu da açık kalır (düğme).
        assert (await istemci.post("/canlilik/tarama", headers=d.girvak.baslik)).status_code == 200

    senaryo(adimlar)


def test_tarama_anahtari_ayari_bos_ya_da_uzun():
    import pytest
    from pydantic import ValidationError

    from app.core.config import Settings

    ortak = {"database_url": "postgresql+asyncpg://x@y/z", "jwt_gizli_anahtar": ANAHTAR}
    assert Settings(**ortak, tarama_anahtari="").tarama_anahtari == ""
    assert Settings(**ortak, tarama_anahtari=ANAHTAR).tarama_anahtari == ANAHTAR
    with pytest.raises(ValidationError):
        Settings(**ortak, tarama_anahtari="kisa")


# --- Yeni fırsat (§ 2) -----------------------------------------------------------------------


async def _firsat_dunyasi(d, *, kart_gun, ihtiyac_gun):
    """E1: kurum1'in ihtiyacı (sektör 'eğitim') genc1'in kartına önerildi; son hareket şimdi."""
    simdi = SIMDI()
    d.kurum1.profil.sektor = "eğitim"
    d.K1.olusturma_tarihi = simdi - dt.timedelta(days=kart_gun)
    d.I1.olusturma_tarihi = simdi - dt.timedelta(days=ihtiyac_gun)
    d.E1.son_aktivite_tarihi = simdi  # öneri yeni: oneri_bekliyor tetiklenmesin
    await d.oturum.commit()


def test_yeni_ihtiyac_eski_karta_anonim_firsat_bir_kez():
    async def adimlar(istemci, d):
        await _firsat_dunyasi(d, kart_gun=20, ihtiyac_gun=2)
        await _tara(d)
        assert [(o.tur, o.alici_hesap_id) for o in await _olaylar(d, d.E1)] == [
            ("yeni_firsat", d.genc1.hesap.id)
        ]
        [bildirim] = await bildirimleri(d, d.genc1)
        assert bildirim.tur == "yeni_firsat"
        assert "eğitim" in bildirim.metin
        assert "Koop" not in bildirim.metin  # kurum adı yok
        assert bildirim.eslesme_id is None  # eşleşmenin varlığı sızmaz

        # İkinci tarama ve araya giren hareket: fırsat bir kez gider.
        d.E1.son_aktivite_tarihi = SIMDI()
        await d.oturum.commit()
        await _tara(d)
        assert len(await _olaylar(d, d.E1)) == 1

        # Gencin bildirim listesi de eşleşme kimliği taşımıyor.
        liste = (await istemci.get("/bildirimler", headers=d.genc1.baslik)).json()
        assert liste[0]["eslesme_id"] is None and liste[0]["isbirligi_id"] is None

    senaryo(adimlar)


def test_firsat_llm_girdisinde_kurum_adi_yok(monkeypatch):
    from app.agents import canlilik

    gorulen = []

    async def kisisel(b):
        gorulen.append(b)
        return None

    monkeypatch.setattr(canlilik, "kisisel_metin", kisisel)

    async def adimlar(istemci, d):
        await _firsat_dunyasi(d, kart_gun=20, ihtiyac_gun=2)
        await _tara(d)
        firsatlar = [b for b in gorulen if b.tur == "yeni_firsat" and b.sektor == "eğitim"]
        assert firsatlar and all(b.karsi_ad == "" for b in firsatlar)

    senaryo(adimlar)


@pytest.mark.parametrize(
    "kart_gun,ihtiyac_gun",
    [(5, 2), (20, 8)],
    ids=["kart-yeni", "ihtiyac-eski"],
)
def test_firsat_kosulu_disinda_bildirim_yok(kart_gun, ihtiyac_gun):
    async def adimlar(istemci, d):
        await _firsat_dunyasi(d, kart_gun=kart_gun, ihtiyac_gun=ihtiyac_gun)
        await _tara(d)
        assert await _olaylar(d, d.E1) == []

    senaryo(adimlar)
