"""Firma–firma eşleştirme (docs/plans/firma-akisi.md § 0 kararlar 5, 11-14, 18; § 3-4).

Aynı eşleşme tablosu, aynı pipeline: ortak ilanının adayları firma kartları.
Kesin şartlar (tür, kendi firması, şehir) SQL'de; benzerlik alt sınırı ve
eşik aynı; bonus doğrulanmış firma ve tamamlanan iş birliği.
"""

from __future__ import annotations

import datetime as dt
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import selectinload

from app.agents.eslestirme import (
    FirmaAdayi,
    eslesme_ekle_ifadesi,
    firma_bonusu,
    firma_guven_ozeti,
    skor_hesapla,
    temizlenecekler,
)
from app.api import canlilik as canlilik_api
from app.api.sahiplik import TARAF_ADAY, TARAF_ILAN, eslesmedeki_taraf, taraf_adi, taraf_hesabi
from app.db.base import EMBEDDING_DIM
from app.models.bildirim import TUR_YENI_ONERI, Bildirim
from app.models.eslesme import Eslesme
from app.models.firma_karti import FirmaKarti
from app.models.hesap import Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.servisler import eslestirme as servis
from app.servisler import firma_karti as firma_servisi
from app.servisler.eslestirme import iletisim, iliskileriyle
from tests.test_sahiplik import _hesap, senaryo

V = [1.0] + [0.0] * (EMBEDDING_DIM - 1)
DIK = [0.0, 1.0] + [0.0] * (EMBEDDING_DIM - 2)

# --- Saf kurallar ----------------------------------------------------------------------


def test_firma_bonusu():
    assert firma_bonusu(False, 0) == 0.0
    assert firma_bonusu(True, 0) == 0.5
    assert firma_bonusu(False, 2) == 0.5
    assert firma_bonusu(True, 1) == 1.0


def test_firma_adayi_ayni_formul():
    aday = FirmaAdayi(firma_karti=SimpleNamespace(id="k"), benzerlik=0.6, dogrulama_bonus=0.5)
    assert aday.skor == pytest.approx(skor_hesapla(0.6, 0.5))
    assert aday.aday_kimligi == "k"


def test_ekleme_ifadesi_aday_turune_gore_cakisma_sutunu():
    firma = str(
        eslesme_ekle_ifadesi(
            ihtiyac_karti_id=uuid.uuid4(), firma_karti_id=uuid.uuid4(), skor=0.7
        ).compile(dialect=postgresql.dialect())
    )
    assert "ON CONFLICT (ihtiyac_karti_id, firma_karti_id) DO NOTHING" in firma
    for hatali in ({}, {"yetenek_karti_id": uuid.uuid4(), "firma_karti_id": uuid.uuid4()}):
        with pytest.raises(ValueError):
            eslesme_ekle_ifadesi(ihtiyac_karti_id=uuid.uuid4(), skor=0.5, **hatali)


def test_temizlik_firma_kimligini_tanir():
    kalan, giden = uuid.uuid4(), uuid.uuid4()
    eslesmeler = [
        SimpleNamespace(yetenek_karti_id=None, firma_karti_id=kalan, durum="onerildi"),
        SimpleNamespace(yetenek_karti_id=None, firma_karti_id=giden, durum="onerildi"),
        SimpleNamespace(yetenek_karti_id=None, firma_karti_id=giden, durum="genc_ilgilendi"),
    ]
    assert temizlenecekler(eslesmeler, [kalan]) == [eslesmeler[1]]


def test_guven_ozeti_dogrulanmamisi_soyler():
    assert "henüz doğrulanmadı" in firma_guven_ozeti(False, 0)
    assert "program ekibi" in firma_guven_ozeti(True, 2)


# --- Gerçek veritabanı -----------------------------------------------------------------


@pytest.fixture(autouse=True)
def gerekce_sahte(monkeypatch):
    async def uret(ihtiyac, aday):
        return f"{aday.firma_karti.kurum.ad} uygun."

    monkeypatch.setattr(servis, "firma_gerekce_uret", uret)


async def _firma(d, ad, tur="girisim", sehir="İstanbul", vektor=V, dogrulandi=False):
    kisi = await _hesap(d.oturum, "kurum", ad)
    kisi.profil.tur, kisi.profil.sehir = tur, sehir
    if dogrulandi:
        kisi.profil.dogrulama_durumu = "dogrulandi"
    kisi.kart = FirmaKarti(
        kurum_id=kisi.profil.id,
        ne_yapiyoruz=f"{ad} işi",
        yetkinlikler=["x"],
        embedding=vektor,
    )
    d.oturum.add(kisi.kart)
    await d.oturum.flush()
    return kisi


async def _ortak_ilan(d, **ek) -> IhtiyacKarti:
    ilan = IhtiyacKarti(
        kurum_id=d.kurum1.profil.id,
        problem_tanimi="Soğuk zincirde kayıp",
        aranan="firma",
        embedding=V,
        **ek,
    )
    d.oturum.add(ilan)
    await d.oturum.commit()
    return ilan


async def _adaylar(d, ilan) -> dict[str, Eslesme]:
    eslesmeler = await servis.pipeline_calistir(d.oturum, ilan)
    return {e.firma_karti.kurum.ad: e for e in eslesmeler}


def test_firma_adaylari_kesin_sartlar_ve_siralama():
    async def adimlar(istemci, d):
        # İlanı açan firmanın kendi kartı da var: önerilmemeli.
        kendi = FirmaKarti(
            kurum_id=d.kurum1.profil.id, ne_yapiyoruz="kendi", yetkinlikler=["x"], embedding=V
        )
        d.oturum.add(kendi)
        await _firma(d, "Dogrulu", dogrulandi=True)
        await _firma(d, "Siradan")
        await _firma(d, "Alakasiz", vektor=DIK)
        await _firma(d, "Kurumsal AS", tur="kurumsal")
        ilan = await _ortak_ilan(d)

        adaylar = await _adaylar(d, ilan)
        assert set(adaylar) == {"Dogrulu", "Siradan", "Kurumsal AS"}
        assert all(e.yetenek_karti_id is None for e in adaylar.values())
        # Doğrulanmış firma aynı benzerlikte öne geçer (bonus), alakasız elenir.
        assert adaylar["Dogrulu"].skor > adaylar["Siradan"].skor
        assert adaylar["Dogrulu"].gerekce_metni == "Dogrulu uygun."
        yeni = await d.oturum.scalar(
            select(func.count())
            .select_from(Bildirim)
            .where(Bildirim.hesap_id == d.kurum1.hesap.id, Bildirim.tur == TUR_YENI_ONERI)
        )
        assert yeni == 1

    senaryo(adimlar)


def test_tur_ve_sehir_sarti():
    async def adimlar(istemci, d):
        await _firma(d, "Girisim Ist")
        await _firma(d, "Kurumsal Ist", tur="kurumsal")
        await _firma(d, "Kurumsal Izmir", tur="kurumsal", sehir="İzmir")

        sadece_kurumsal = await _ortak_ilan(d, aranan_firma_turleri=["kurumsal"])
        assert set(await _adaylar(d, sadece_kurumsal)) == {"Kurumsal Ist", "Kurumsal Izmir"}

        izmirde = await _ortak_ilan(d, sehir_tercihi="izmir")
        assert set(await _adaylar(d, izmirde)) == {"Kurumsal Izmir"}

    senaryo(adimlar)


def test_firmalar_genc_ilanina_gencler_ortak_ilanina_girmez():
    async def adimlar(istemci, d):
        await _firma(d, "Aday Firma")
        # Genç ilanı (I1) aynı vektörle: firma kartı buraya aday değil.
        genc_ilani = await d.oturum.get(IhtiyacKarti, d.I1.id)
        genc_ilani.embedding = V
        await d.oturum.commit()
        eslesmeler = await servis.pipeline_calistir(d.oturum, genc_ilani)
        assert all(e.firma_karti_id is None for e in eslesmeler)

    senaryo(adimlar)


def test_karar_verilmis_firma_kaydi_korunur():
    async def adimlar(istemci, d):
        aday = await _firma(d, "Aday Firma")
        ilan = await _ortak_ilan(d)
        eslesme = (await _adaylar(d, ilan))["Aday Firma"]
        eslesme.durum = "genc_ilgilendi"
        eslesme.skor, eslesme.gerekce_metni = 0.9, "eski gerekçe"
        await d.oturum.commit()

        # Kart artık alakasız: pipeline onerildi olsa silerdi, ilgi gösterilmiş kaydı silmez.
        aday.kart.embedding = DIK
        await d.oturum.commit()
        kalan = await _adaylar(d, ilan)
        assert kalan["Aday Firma"].skor == 0.9
        assert kalan["Aday Firma"].gerekce_metni == "eski gerekçe"

    senaryo(adimlar)


async def _hesabi_oku(d, kisi) -> Hesap:
    return await d.oturum.scalar(
        select(Hesap)
        .options(selectinload(Hesap.kurum), selectinload(Hesap.kullanici))
        .where(Hesap.id == kisi.hesap.id)
        .execution_options(populate_existing=True)
    )


def test_taraflar_iletisim_ve_ilgi_henuz_kapali():
    async def adimlar(istemci, d):
        aday = await _firma(d, "Aday Firma")
        ilan = await _ortak_ilan(d)
        eslesme_id = (await _adaylar(d, ilan))["Aday Firma"].id
        eslesme = await d.oturum.scalar(
            iliskileriyle(select(Eslesme)).where(Eslesme.id == eslesme_id)
        )
        adayin, ilanin, baska, genc = [
            await _hesabi_oku(d, k) for k in (aday, d.kurum1, d.kurum2, d.genc1)
        ]

        assert eslesmedeki_taraf(adayin, eslesme) == TARAF_ADAY
        assert eslesmedeki_taraf(ilanin, eslesme) == TARAF_ILAN
        assert eslesmedeki_taraf(baska, eslesme) is None
        assert eslesmedeki_taraf(genc, eslesme) is None
        assert taraf_adi(eslesme, TARAF_ADAY) == "Aday Firma"
        assert taraf_hesabi(eslesme, TARAF_ADAY) == adayin.id

        eslesme.durum = "kabul_edildi"
        acik = iletisim(eslesme, ilanin)
        assert acik.aday_firma_email == adayin.kurum.iletisim_email
        assert acik.genc_email is None
        assert iletisim(eslesme, baska) is None
        await d.oturum.rollback()

        # Firmalar arası ilgi 8. adımda: şimdilik anlaşılır 409; taraf değilse 404.
        ilgi = await istemci.post(
            "/eslestirme/ilgileniyorum",
            headers=d.kurum1.baslik,
            json={"eslesme_id": str(eslesme_id)},
        )
        assert ilgi.status_code == 409
        assert "yakında" in ilgi.json()["detail"]
        yabanci = await istemci.post(
            "/eslestirme/ilgileniyorum",
            headers=d.kurum2.baslik,
            json={"eslesme_id": str(eslesme_id)},
        )
        assert yabanci.status_code == 404

    senaryo(adimlar)


def test_firma_karti_hazirlaninca_ortak_ilanlariyla_eslesir(monkeypatch):
    async def embedding(_metin, girdi_turu="document"):
        return V

    monkeypatch.setattr(firma_servisi, "embedding_uret", embedding)

    async def adimlar(istemci, d):
        ilan = await _ortak_ilan(d)
        sonradan = await _firma(d, "Sonradan Gelen", vektor=None)
        kart_id = sonradan.kart.id
        await d.oturum.commit()

        assert await firma_servisi.firma_kartini_hazirla_oturumla(d.oturum, kart_id, 1)
        eslesme = await d.oturum.scalar(
            select(Eslesme).where(
                Eslesme.ihtiyac_karti_id == ilan.id, Eslesme.firma_karti_id == kart_id
            )
        )
        assert eslesme is not None and eslesme.durum == "onerildi"

    senaryo(adimlar)


def test_kart_icerigi_degisince_bekleyen_onerinin_gerekcesi_bosalir():
    async def adimlar(istemci, d):
        aday = await _firma(d, "Aday Firma")
        ilan = await _ortak_ilan(d)
        eslesme_id = (await _adaylar(d, ilan))["Aday Firma"].id

        yanit = await istemci.patch(
            "/kurum/kart", headers=aday.baslik, json={"ne_yapiyoruz": "Yeni iş tanımı"}
        )
        assert yanit.status_code == 200
        eslesme = await d.oturum.scalar(
            select(Eslesme)
            .where(Eslesme.id == eslesme_id)
            .execution_options(populate_existing=True)
        )
        assert eslesme.gerekce_metni is None

    senaryo(adimlar)


def test_canlilik_firma_eslesmelerini_taramaz():
    async def adimlar(istemci, d):
        await _firma(d, "Aday Firma")
        ilan = await _ortak_ilan(d)
        eslesme = (await _adaylar(d, ilan))["Aday Firma"]
        eslesme.son_aktivite_tarihi = dt.datetime.now(dt.UTC) - dt.timedelta(days=60)
        await d.oturum.commit()

        adaylar = await canlilik_api.pasif_adaylar(
            d.oturum, dt.datetime.now(dt.UTC), dt.date.today()
        )
        assert eslesme.id not in {e.id for e, _, _ in adaylar}

    senaryo(adimlar)


def test_oneriler_ucu_firma_karti_doner_eposta_yok():
    async def adimlar(istemci, d):
        await _firma(d, "Dogrulu", dogrulandi=True)
        ilan = await _ortak_ilan(d)
        await servis.pipeline_calistir(d.oturum, ilan)

        yanit = await istemci.get(
            f"/eslestirme/oneriler/{d.kurum1.profil.id}",
            params={"ihtiyac_karti_id": str(ilan.id)},
            headers=d.kurum1.baslik,
        )
        assert yanit.status_code == 200
        oneri = yanit.json()["oneriler"][0]
        assert oneri["aday_turu"] == "firma"
        assert oneri["yetenek_karti"] is None
        firma = oneri["firma_karti"]
        assert firma["firma_adi"] == "Dogrulu"
        assert firma["dogrulandi"] is True
        assert firma["yetkinlikler"] == ["x"]
        assert "@" not in yanit.text  # e-posta yok (karşılıklı ilgi yok)

        panel = (await istemci.get("/eslestirme/onerilerim", headers=d.kurum1.baslik)).json()
        satir = next(s for s in panel if s["ihtiyac_karti_id"] == str(ilan.id))
        assert satir["aday_turu"] == "firma"
        assert satir["aday_adi"] == "Dogrulu"
        assert satir["genc_adi"] is None

    senaryo(adimlar)
