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

from app.agents.dogrulama.cikarim import KanitCikarimi
from app.agents.dogrulama.kurallar import OkunanKanit
from app.api.auth import hesap_olustur
from app.core.kanit_okuma.belge import ErisimDurumu, KaynakSeviyesi
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
from tests.kanit_yardimcisi import link_parcasi
from tests.test_profil import HazirTaslakGrafigi, _embedding_sahte
from tests.veritabani import api_istemcisi, geri_alinan_oturum

# --- Saf kural ------------------------------------------------------------------------------


def _rastgele_yon() -> list[float]:
    """Yerel veritabanındaki gerçek kartlarla karışmasın diye rastgele bir yön."""
    vektor = [random.gauss(0, 1) for _ in range(EMBEDDING_DIM)]
    boy = math.sqrt(sum(x * x for x in vektor))
    return [x / boy for x in vektor]


def _email() -> str:
    return f"test-{uuid.uuid4().hex[:10]}@ornek.com"


@pytest.fixture
def sahte_dis_servisler(monkeypatch):
    """Link kontrolü, model çıkarımı ve gerekçe sahte; çıkarım çağrıları sayılır."""
    cagrilar: list[str] = []

    async def oku(url, _sorgular, **_):
        return OkunanKanit(
            erisim=ErisimDurumu.ACIK,
            seviye=KaynakSeviyesi.KAMUYA_ACIK,
            metin="Proje sayfası",
            url=url,
        )

    async def cikar(alanlar):
        cagrilar.append(alanlar["baslik"])
        return KanitCikarimi(
            ilgili_mi=True,
            sonuc_var=True,
            sonuc_sayisal=True,
            sonuc_olcut_acik=True,
            pay_var=True,
            pay_ozgul=True,
        )

    async def gerekce(_ihtiyac, _aday):
        return "Kartlardaki somut noktalar örtüşüyor."

    monkeypatch.setattr(dogrulama_servisi, "kanit_oku", oku)
    monkeypatch.setattr(dogrulama_servisi, "cikar", cikar)
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
            SomutCikti(
                baslik="Linkli iş", kanit_parcalari=[link_parcasi("https://github.com/elif/proje")]
            ),
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

            # Her kalem bir kez değerlendirildi; linksiz kalem de (karar 10).
            assert sorted(sahte_dis_servisler) == ["Linkli iş", "Linksiz iş"]
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
            # Herkese açık link seviye C: Kanıt 2. Linksiz kalemde Kanıt "—", beyan 2.
            assert ciktilar["Linkli iş"].guven_skoru.kanit_orijinalligi == 2
            assert ciktilar["Linksiz iş"].guven_skoru.kanit_orijinalligi is None
            assert ciktilar["Linksiz iş"].guven_skoru.sonuc_olculebilirligi == 2

            # Puan eşleşme skoruna girdi: benzerlik 1.0; bonus iki kalemin ortalaması,
            # (2+2+2)/9 ve (2+2)/6, ikisi de 2/3. Boş başlık paydaya girmez.
            eslesme = await oturum.scalar(
                select(Eslesme).where(Eslesme.yetenek_karti_id == kart.id)
            )
            assert eslesme.skor == pytest.approx(0.75 + 0.25 * 2 / 3, abs=1e-3)

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
