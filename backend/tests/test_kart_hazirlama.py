"""Kart hazırlama: otomatik puanlama ve yeniden eşleştirme (docs/plans/genc-akisi.md § 5.5).

Açık: sonradan gelen genç, önceden açılmış ihtiyaçlarla eşleşmiyordu (eşleştirme
yalnızca ihtiyaç kartı onaylanınca çalışıyordu). Kart hazırlama mevcut
pipeline'ı kartla ilgili her ihtiyaç kartı için çalıştırır.
"""

import asyncio
import math
import random
import uuid

import pytest
from sqlalchemy import func, select

from app.agents.dogrulama import LinkKontrolu, RubrikPuani, otomatik_puanlanir_mi
from app.api.auth import hesap_olustur
from app.core.kimlik import token_uret
from app.db.base import EMBEDDING_DIM
from app.main import app
from app.models.bildirim import TUR_YENI_ONERI, Bildirim
from app.models.eslesme import Eslesme
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler import eslestirme as eslestirme_servisi
from app.servisler import kart_hazirlama
from app.servisler.dogrulama import kanit as dogrulama_servisi
from tests.test_profil import HazirTaslakGrafigi, _embedding_sahte
from tests.veritabani import api_istemcisi, geri_alinan_oturum

# --- Saf kural ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("link", "puanlanmis", "beklenen"),
    [
        ("https://github.com/elif/proje", False, True),
        ("https://github.com/elif/proje", True, False),  # zaten puanlı: LLM yok
        (None, False, False),  # linksiz: "doğrulanmamış", nötr
        ("   ", False, False),
    ],
)
def test_otomatik_puanlanir_mi(link, puanlanmis, beklenen):
    assert otomatik_puanlanir_mi(link, puanlanmis) is beklenen


# --- Gerçek veritabanında -------------------------------------------------------------------


def _rastgele_yon() -> list[float]:
    """Yerel veritabanındaki gerçek kartlarla karışmasın diye rastgele bir yön."""
    vektor = [random.gauss(0, 1) for _ in range(EMBEDDING_DIM)]
    boy = math.sqrt(sum(x * x for x in vektor))
    return [x / boy for x in vektor]


def _email() -> str:
    return f"test-{uuid.uuid4().hex[:10]}@ornek.com"


@pytest.fixture
def sahte_dis_servisler(monkeypatch):
    """Link kontrolü, rubrik ve gerekçe sahte; rubrik çağrıları sayılır."""
    cagrilar: list[str] = []

    async def link(adres):
        return LinkKontrolu(True, 200, "Proje sayfası", "açılıyor")

    async def rubrik(*, baslik, **_):
        cagrilar.append(baslik)
        return RubrikPuani(
            kanit_orijinalligi=3, sonuc_olculebilirligi=2, rol_netligi=2, gerekce_metni="g"
        )

    async def gerekce(_ihtiyac, _aday):
        return "Kartlardaki somut noktalar örtüşüyor."

    monkeypatch.setattr(dogrulama_servisi, "linki_kontrol_et", link)
    monkeypatch.setattr(dogrulama_servisi, "rubrik_puanla", rubrik)
    monkeypatch.setattr(eslestirme_servisi, "gerekce_uret", gerekce)
    return cagrilar


async def _kurum_ve_ihtiyac(oturum, yon):
    hesap = await hesap_olustur(
        oturum, email=_email(), sifre="yeterince-uzun", rol="kurum", ad="Koop"
    )
    kurum = await oturum.scalar(select(Kurum).where(Kurum.hesap_id == hesap.id))
    ihtiyac = IhtiyacKarti(kurum_id=kurum.id, problem_tanimi="p", embedding=yon)
    oturum.add(ihtiyac)
    await oturum.flush()
    return kurum, ihtiyac


async def _gencin_karti(oturum, yon, *, versiyon=1):
    hesap = await hesap_olustur(
        oturum, email=_email(), sifre="yeterince-uzun", rol="genc", ad="Elif"
    )
    kullanici = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
    kart = YetenekKarti(
        kullanici_id=kullanici.id,
        rol_alani="backend geliştirici",
        deneyim_seviyesi="orta",
        embedding=yon,
        versiyon=versiyon,
        somut_ciktilar=[
            SomutCikti(baslik="Linkli iş", kanit_linki="https://github.com/elif/proje"),
            SomutCikti(baslik="Linksiz iş"),
        ],
    )
    oturum.add(kart)
    await oturum.commit()
    return kart


def test_sonradan_gelen_genc_mevcut_ihtiyacla_eslesir_ve_is_idempotent(sahte_dis_servisler):
    async def senaryo():
        async with geri_alinan_oturum() as oturum:
            yon = _rastgele_yon()
            kurum, ihtiyac = await _kurum_ve_ihtiyac(oturum, yon)  # önce ihtiyaç
            kart = await _gencin_karti(oturum, yon)  # sonra genç

            for _ in range(2):  # aynı iş iki kez sıraya girdi
                await kart_hazirlama.karti_hazirla_oturumla(oturum, kart.id, kart.versiyon)

            eslesmeler = await oturum.scalar(
                select(func.count())
                .select_from(Eslesme)
                .where(Eslesme.ihtiyac_karti_id == ihtiyac.id, Eslesme.yetenek_karti_id == kart.id)
            )
            assert eslesmeler == 1
            bildirimler = await oturum.scalar(
                select(func.count())
                .select_from(Bildirim)
                .where(Bildirim.hesap_id == kurum.hesap_id, Bildirim.tur == TUR_YENI_ONERI)
            )
            assert bildirimler == 1

            # Linkli kalem bir kez puanlandı; linksiz kalem nötr kaldı.
            assert sahte_dis_servisler == ["Linkli iş"]
            ciktilar = {
                c.baslik: c
                for c in await oturum.scalars(
                    select(SomutCikti)
                    .where(SomutCikti.yetenek_karti_id == kart.id)
                    .execution_options(populate_existing=True)
                )
            }
            await oturum.refresh(ciktilar["Linkli iş"], ["guven_skoru"])
            await oturum.refresh(ciktilar["Linksiz iş"], ["guven_skoru"])
            assert ciktilar["Linkli iş"].guven_skoru.kanit_orijinalligi == 3
            assert ciktilar["Linksiz iş"].guven_skoru is None

            # Puan eşleşme skoruna girdi: benzerlik 1.0, bonus (3+2+2+0)/12 tek kalemden.
            eslesme = await oturum.scalar(
                select(Eslesme).where(Eslesme.yetenek_karti_id == kart.id)
            )
            assert eslesme.skor == pytest.approx(0.75 + 0.25 * 7 / 12, abs=1e-3)

    asyncio.run(senaryo())


def test_ilgisiz_ihtiyac_icin_pipeline_calismaz():
    async def senaryo():
        async with geri_alinan_oturum() as oturum:
            yon = _rastgele_yon()
            _, ilgili = await _kurum_ve_ihtiyac(oturum, yon)
            _, ilgisiz = await _kurum_ve_ihtiyac(oturum, [-x for x in yon])
            kart = await _gencin_karti(oturum, yon)

            idler = await kart_hazirlama.ilgili_ihtiyac_kartlari(oturum, kart.id)
            assert ilgili.id in idler
            assert ilgisiz.id not in idler

    asyncio.run(senaryo())


def test_eski_versiyonun_isi_hicbir_sey_yapmaz(sahte_dis_servisler):
    """Kart bu arada değişti (versiyon 2); versiyon 1 için sıraya giren iş çıkar."""

    async def senaryo():
        async with geri_alinan_oturum() as oturum:
            yon = _rastgele_yon()
            _, ihtiyac = await _kurum_ve_ihtiyac(oturum, yon)
            kart = await _gencin_karti(oturum, yon, versiyon=2)

            await kart_hazirlama.karti_hazirla_oturumla(oturum, kart.id, 1)

            assert sahte_dis_servisler == []
            assert (
                await oturum.scalar(
                    select(func.count())
                    .select_from(Eslesme)
                    .where(Eslesme.ihtiyac_karti_id == ihtiyac.id)
                )
                == 0
            )

    asyncio.run(senaryo())


def test_kart_onayi_hazirlamayi_siraya_koyar(monkeypatch, kart_hazirlama_arka_plani_yok):
    _embedding_sahte(monkeypatch)

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap = await hesap_olustur(
                oturum, email=_email(), sifre="yeterince-uzun", rol="genc", ad="Elif"
            )
            kullanici = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
            kullanici.sehir = "İstanbul"
            await oturum.commit()
            baslik = {"Authorization": f"Bearer {token_uret(hesap.id, 'genc')}"}
            taslak = {
                "rol_alani": "backend geliştirici",
                "deneyim_seviyesi": "orta",
                "sektor_ilgi_alani": ["eğitim"],
                "somut_ciktilar": [{"baslik": "İş"}],
            }
            app.state.kesif_grafigi = HazirTaslakGrafigi(hesap.id, taslak)
            oturum_id = str(uuid.uuid4())
            try:
                ilk = await istemci.post(
                    "/kesif/kart/onayla", headers=baslik, json={"oturum_id": oturum_id}
                )
                tekrar = await istemci.post(
                    "/kesif/kart/onayla", headers=baslik, json={"oturum_id": oturum_id}
                )
            finally:
                del app.state.kesif_grafigi

            assert (ilk.status_code, tekrar.status_code) == (201, 200)
            kart_id = uuid.UUID(ilk.json()["id"])
            # İkisi de aynı kart için sıraya koydu; iş idempotent.
            assert kart_hazirlama_arka_plani_yok == [(kart_id, 1, False), (kart_id, 1, False)]

    asyncio.run(senaryo())
