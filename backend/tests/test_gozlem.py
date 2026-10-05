"""Kalıcı gözlem (plan § 10.3, § 14.4, adım 12): kayıtlar, panel ucu, saklama süresi."""

import asyncio
import contextlib
import datetime as dt

import pytest
from sqlalchemy import func, select

from app.agents.dogrulama.gozlem import erisim_dagilimi, servis_adi
from app.core.dis_servisler.saglik import SaglikKaydi
from app.models.gozlem import (
    DegerlendirmeGozlemi,
    KanitGozlemi,
    ServisGunlugu,
)
from app.servisler import gozlem
from app.servisler.dogrulama import degerlendir
from tests.test_kanit_parcasi import (  # noqa: F401
    _genc_ve_kalem,
    _kalemi_oku,
    sahte_degerlendirme,
)
from tests.test_sahiplik import senaryo
from tests.veritabani import geri_alinan_oturum

SIMDI = dt.datetime(2026, 10, 5, tzinfo=dt.UTC)


# --- Saf -----------------------------------------------------------------------------------


def test_erisim_dagilimi_platform_basina_sayar_ve_oran_verir():
    sonuc = erisim_dagilimi(
        [
            ("github", "acik", 8),
            ("github", "bulunamadi", 2),
            ("behance", "acik", 1),
            ("behance", "engellendi", 3),
            ("medium", "acik", 1),
        ]
    )
    assert [p.platform for p in sonuc] == ["github", "behance", "medium"]  # çok okunan önce
    github = sonuc[0]
    assert github.toplam == 10
    assert github.acik_orani == pytest.approx(0.8)
    assert github.erisimler["engellendi"] == 0  # olmayan durum 0 yazılır
    assert sonuc[1].acik_orani == pytest.approx(0.25)


def test_servis_adi_saglayiciya_ozgu_kaydi_indirger():
    assert servis_adi("oauth_github") == "oauth"
    assert servis_adi("eposta") == "eposta"


def test_saglik_kaydi_kalici_kancayi_cagirir_ve_hata_mesaji_tasimaz():
    olaylar = []
    kayit = SaglikKaydi(kalici=lambda *a: olaylar.append(a))
    kayit.basari("eposta")
    kayit.hata("eposta", ValueError("gizli: anahtar=abc"))
    assert olaylar == [("eposta", True, None), ("eposta", False, "ValueError")]


# --- Veritabanı ----------------------------------------------------------------------------


@contextlib.contextmanager
def _oturumu_ver(monkeypatch, oturum):
    """`servis_olayi_yaz` kendi oturumunu açar; testte geri alınan oturum verilir."""

    @contextlib.asynccontextmanager
    async def acici():
        yield oturum

    monkeypatch.setattr(gozlem, "get_sessionmaker", lambda: acici)
    yield


def test_servis_olayi_gun_icinde_toplanir_ve_son_hata_turunu_tutar(monkeypatch):
    async def senaryo_():
        async with geri_alinan_oturum() as oturum:
            with _oturumu_ver(monkeypatch, oturum):
                await gozlem.servis_olayi_yaz("test_servisi", True)
                await gozlem.servis_olayi_yaz("test_servisi", False, "TimeoutError")
                await gozlem.servis_olayi_yaz("test_servisi", True)
            satir = await oturum.scalar(
                select(ServisGunlugu).where(ServisGunlugu.servis == "test_servisi")
            )
            assert (satir.basari_sayisi, satir.hata_sayisi) == (2, 1)
            assert satir.son_hata_turu == "TimeoutError"
            assert satir.son_basari is not None and satir.son_hata is not None

    asyncio.run(senaryo_())


@pytest.mark.usefixtures("sahte_degerlendirme")
def test_degerlendirme_link_okumasini_ve_model_cagrisini_kaydeder():
    async def senaryo_():
        async with geri_alinan_oturum() as oturum:
            _baslik, _kart, kalem_id = await _genc_ve_kalem(
                oturum, link="https://github.com/ornek/kutuphane"
            )
            okuma_once = await oturum.scalar(select(func.count()).select_from(KanitGozlemi))
            degerlendirme_once = await oturum.scalar(
                select(func.count()).select_from(DegerlendirmeGozlemi)
            )
            kalem = await _kalemi_oku(oturum, kalem_id)
            await degerlendir(oturum, kalem)
            await oturum.flush()

            assert await oturum.scalar(select(func.count()).select_from(KanitGozlemi)) == (
                okuma_once + 1
            )
            satir = (
                await oturum.scalars(
                    select(KanitGozlemi).order_by(KanitGozlemi.tarih.desc()).limit(1)
                )
            ).one()
            assert satir.kaynak == "degerlendirme"
            assert satir.erisim == "acik"
            assert satir.okuyucu == "dogrudan"
            assert satir.platform == "web"
            assert satir.sure_ms is not None and satir.girdi_ozeti

            assert await oturum.scalar(select(func.count()).select_from(DegerlendirmeGozlemi)) == (
                degerlendirme_once + 1
            )

    asyncio.run(senaryo_())


def test_eski_gozlemler_90_gun_sonra_silinir():
    async def senaryo_():
        async with geri_alinan_oturum() as oturum:
            eski = SIMDI - dt.timedelta(days=91)
            yeni = SIMDI - dt.timedelta(days=89)
            for tarih in (eski, yeni):
                oturum.add(
                    KanitGozlemi(
                        tarih=tarih,
                        kaynak="yoklama",
                        platform="test-platformu",
                        okuyucu="dogrudan",
                        erisim="acik",
                    )
                )
            oturum.add(ServisGunlugu(servis="test_servisi", gun=eski.date()))
            await oturum.flush()
            await gozlem.eski_gozlemleri_temizle(oturum, SIMDI)
            kalan = list(
                await oturum.scalars(
                    select(KanitGozlemi.tarih).where(KanitGozlemi.platform == "test-platformu")
                )
            )
            assert kalan == [yeni]
            assert (
                await oturum.scalar(
                    select(func.count())
                    .select_from(ServisGunlugu)
                    .where(ServisGunlugu.servis == "test_servisi")
                )
                == 0
            )

    asyncio.run(senaryo_())


def test_gozlem_ucu_yalnizca_girvak_ve_dagilim_ile_servisleri_doner():
    async def adimlar(istemci, d):
        assert (await istemci.get("/girvak/gozlem")).status_code == 401
        assert (await istemci.get("/girvak/gozlem", headers=d.genc1.baslik)).status_code == 403

        simdi = dt.datetime.now(dt.UTC)
        for erisim in ("acik", "acik", "bulunamadi"):
            d.oturum.add(
                KanitGozlemi(
                    kaynak="yoklama",
                    platform="test-platformu",
                    okuyucu="dogrudan",
                    erisim=erisim,
                    tarih=simdi,
                )
            )
        d.oturum.add(
            ServisGunlugu(
                servis="oauth_github",
                gun=simdi.date(),
                basari_sayisi=4,
                hata_sayisi=1,
                son_hata=simdi,
                son_hata_turu="HTTPStatusError",
            )
        )
        await d.oturum.flush()

        yanit = await istemci.get("/girvak/gozlem?gun=7", headers=d.girvak.baslik)
        assert yanit.status_code == 200
        govde = yanit.json()
        assert govde["gun"] == 7
        platform = next(p for p in govde["erisim"] if p["platform"] == "test-platformu")
        assert platform["toplam"] == 3
        assert platform["erisimler"]["acik"] == 2
        assert platform["acik_orani"] == pytest.approx(0.667, abs=0.001)
        servisler = {s["servis"]: s for s in govde["servisler"]}
        assert {"eposta", "yedek_okuyucu", "gorsel_arayici"} <= set(servisler)
        # oauth_github, "oauth" satırına toplanır; yerel kayıtlara ek olarak en az bizimki.
        assert servisler["oauth"]["basari_sayisi"] >= 4
        assert servisler["oauth"]["hata_sayisi"] >= 1
        assert "@" not in str(govde)
        assert set(govde["degerlendirme"]) == {
            "sayi",
            "ortalama_sure_ms",
            "girdi_token",
            "cikti_token",
        }

        assert (
            await istemci.get("/girvak/gozlem?gun=0", headers=d.girvak.baslik)
        ).status_code == 422

    senaryo(adimlar)


def test_kullanim_toplayici_model_cagrilarinin_tokenlarini_toplar():
    import types
    import uuid

    from app.core.llm import SureOlcer, kullanim_topla

    def yanit(girdi, cikti):
        mesaj = types.SimpleNamespace(
            usage_metadata={"input_tokens": girdi, "output_tokens": cikti, "total_tokens": 0}
        )
        return types.SimpleNamespace(generations=[[types.SimpleNamespace(message=mesaj)]])

    olcer = SureOlcer("test", "model-x")
    with kullanim_topla() as kullanim:
        for girdi, cikti in ((100, 10), (50, 5)):
            kimlik = uuid.uuid4()
            olcer.on_llm_start({}, [], run_id=kimlik)
            olcer.on_llm_end(yanit(girdi, cikti), run_id=kimlik)
    assert (kullanim.cagri, kullanim.girdi_token, kullanim.cikti_token) == (2, 150, 15)

    # Toplayıcı dışında çağrı hiçbir şeyi bozmaz.
    kimlik = uuid.uuid4()
    olcer.on_llm_start({}, [], run_id=kimlik)
    olcer.on_llm_end(yanit(1, 1), run_id=kimlik)
