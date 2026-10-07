"""Link çürümesi (docs/dogrulama.md § 10.4): saf sayaç kuralları ve yoklamanın modele
etkisi."""

import asyncio
import datetime as dt

import pytest
from sqlalchemy import select

from app.agents.dogrulama.curume import (
    CURUME_ESIGI,
    curumus_mu,
    sayac_gecisi,
    yoklanacak_mi,
)
from app.core.kanit_okuma.belge import ErisimDurumu
from app.models.bildirim import TUR_KANIT_CURUDU, Bildirim
from app.servisler.dogrulama import curume_yoklamasi
from tests.test_kanit_parcasi import (  # noqa: F401
    _genc_ve_kalem,
    _kalemi_oku,
    sahte_degerlendirme,
)
from tests.veritabani import geri_alinan_oturum

LINK = "https://github.com/ornek/kutuphane"
SIMDI = dt.datetime(2026, 10, 5, tzinfo=dt.UTC)


# --- Saf kurallar ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("erisim", "beklenen"),
    [
        (ErisimDurumu.BULUNAMADI, 2),
        (ErisimDurumu.GIRIS_GEREKLI, 2),
        (ErisimDurumu.ENGELLENDI, 1),
        (ErisimDurumu.HATA, 1),
        (ErisimDurumu.ICERIK_YOK, 1),
        (ErisimDurumu.ACIK, 0),
    ],
)
def test_sayac_yalniz_silinmis_ya_da_gizli_sayar(erisim, beklenen):
    assert sayac_gecisi(1, erisim) == beklenen


def test_esik_uc():
    assert not curumus_mu(CURUME_ESIGI - 1)
    assert curumus_mu(CURUME_ESIGI)


def test_yoklama_yalniz_eskiden_acik_linke_ve_haftada_bir():
    # Baştan giriş isteyen / bulunamayan link yoklanmaz.
    assert not yoklanacak_mi("giris_gerekli", 0, None, SIMDI)
    assert not yoklanacak_mi(None, 0, None, SIMDI)
    # Eskiden açık: hiç yoklanmadıysa yoklanır, 7 günden önce yeniden yoklanmaz.
    assert yoklanacak_mi("acik", 0, None, SIMDI)
    assert not yoklanacak_mi("acik", 0, SIMDI - dt.timedelta(days=6), SIMDI)
    assert yoklanacak_mi("acik", 0, SIMDI - dt.timedelta(days=7), SIMDI)
    # Sayaç işliyorsa erişim alanı ne olursa olsun devam eder.
    assert yoklanacak_mi("giris_gerekli", 1, None, SIMDI)
    # İşlenmemiş eşik beklemeden yeniden denenir.
    assert yoklanacak_mi("acik", 3, SIMDI, SIMDI, isleme_bekliyor=True)


# --- Model ----------------------------------------------------------------------------------


def _okuyucu(durum: dict):
    """Yalnızca bu testin linki için `durum["erisim"]`; başka linkler nötr."""

    async def oku(url):
        return durum["erisim"] if url == LINK else ErisimDurumu.ENGELLENDI

    return oku


@pytest.mark.usefixtures("sahte_degerlendirme")
def test_uc_yoklamada_curuyunca_kanit_bos_kalir_gence_haber_gider_gecmis_saklanir():
    async def senaryo():
        async with geri_alinan_oturum() as oturum:
            _baslik, _kart_id, kalem_id = await _genc_ve_kalem(oturum, link=LINK)
            kalem = await _kalemi_oku(oturum, kalem_id)
            # Link eskiden açık okunmuş ve Kanıt 2 almış.
            kalem.kanit_parcalari[0].erisim = "acik"
            from app.servisler.dogrulama import degerlendir

            await degerlendir(oturum, kalem)
            await oturum.commit()
            assert kalem.guven_skoru.kanit_orijinalligi == 2

            durum = {"erisim": ErisimDurumu.BULUNAMADI}
            oku = _okuyucu(durum)
            sonuclar = []
            for hafta in range(1, 4):
                sonuclar.append(
                    await curume_yoklamasi(oturum, SIMDI + dt.timedelta(days=8 * hafta), oku)
                )
                await oturum.commit()
            assert [s.curuyen for s in sonuclar] == [0, 0, 1]

            kalem = await _kalemi_oku(oturum, kalem_id)
            parca = kalem.kanit_parcalari[0]
            assert parca.curume_sayaci == 3
            assert parca.belge["curume"]["onceki_puanlar"]["kanit"] == 2
            assert kalem.guven_skoru.kanit_orijinalligi is None  # "—"
            assert kalem.guven_skoru.degerlendirme_tarihi is not None
            bildirimler = list(
                await oturum.scalars(select(Bildirim).where(Bildirim.tur == TUR_KANIT_CURUDU))
            )
            assert len(bildirimler) == 1
            assert "Kütüphane" in bildirimler[0].metin
            assert "@" not in bildirimler[0].metin

            # Dördüncü yoklama aynı haberi tekrar yazmaz.
            sonuc = await curume_yoklamasi(oturum, SIMDI + dt.timedelta(days=40), oku)
            assert sonuc.curuyen == 0

    asyncio.run(senaryo())


@pytest.mark.usefixtures("sahte_degerlendirme")
def test_engel_ve_hata_sayilmaz_acik_sayaci_sifirlar_ve_toparlanma_yeniden_puanlar():
    async def senaryo():
        async with geri_alinan_oturum() as oturum:
            _baslik, _kart_id, kalem_id = await _genc_ve_kalem(oturum, link=LINK)
            kalem = await _kalemi_oku(oturum, kalem_id)
            kalem.kanit_parcalari[0].erisim = "acik"
            await oturum.commit()

            durum = {"erisim": ErisimDurumu.BULUNAMADI}
            oku = _okuyucu(durum)
            gun = 0

            async def yokla(erisim):
                nonlocal gun
                gun += 8
                durum["erisim"] = erisim
                sonuc = await curume_yoklamasi(oturum, SIMDI + dt.timedelta(days=gun), oku)
                await oturum.commit()
                return sonuc

            await yokla(ErisimDurumu.BULUNAMADI)
            await yokla(ErisimDurumu.ENGELLENDI)  # sayılmaz
            await yokla(ErisimDurumu.HATA)  # sayılmaz
            kalem = await _kalemi_oku(oturum, kalem_id)
            assert kalem.kanit_parcalari[0].curume_sayaci == 1

            await yokla(ErisimDurumu.ACIK)  # sıfırlar
            kalem = await _kalemi_oku(oturum, kalem_id)
            assert kalem.kanit_parcalari[0].curume_sayaci == 0

            for _ in range(3):
                await yokla(ErisimDurumu.GIRIS_GEREKLI)
            kalem = await _kalemi_oku(oturum, kalem_id)
            assert kalem.kanit_parcalari[0].curume_sayaci == 3
            assert kalem.guven_skoru.kanit_orijinalligi is None

            sonuc = await yokla(ErisimDurumu.ACIK)  # link geri geldi
            assert sonuc.iyilesen == 1
            kalem = await _kalemi_oku(oturum, kalem_id)
            assert kalem.kanit_parcalari[0].curume_sayaci == 0
            assert "curume" not in kalem.kanit_parcalari[0].belge
            assert kalem.guven_skoru.kanit_orijinalligi == 2

    asyncio.run(senaryo())


@pytest.mark.usefixtures("sahte_degerlendirme")
def test_baslangicta_giris_isteyen_link_yoklanmaz():
    async def senaryo():
        async with geri_alinan_oturum() as oturum:
            _baslik, _kart_id, kalem_id = await _genc_ve_kalem(oturum, link=LINK)
            kalem = await _kalemi_oku(oturum, kalem_id)
            kalem.kanit_parcalari[0].erisim = "giris_gerekli"  # LinkedIn gibi
            await oturum.commit()
            okunanlar: list[str] = []

            async def oku(url):
                okunanlar.append(url)
                return ErisimDurumu.BULUNAMADI

            await curume_yoklamasi(oturum, SIMDI, oku)
            assert LINK not in okunanlar

    asyncio.run(senaryo())
