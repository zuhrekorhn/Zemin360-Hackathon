"""Kart ve profil düzenleme (docs/plans/genc-akisi.md § 6).

Temel kural: doğrulanmış bir iş kaleminin içeriği ya da linki değişirse o
kalemin güven göstergesi sıfırlanır; değişmeyenlerinki korunur. Değişiklikten
önceki referans yanıtları silinmez ama puana girmez.
"""

import asyncio
import datetime as dt
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.dogrulama import (
    DURUM_BEKLIYOR,
    DURUM_YANIT_YOK,
    DURUM_YANITLANDI,
    ReferansYaniti,
    gecerli_referans_yanitlari,
    referans_gecerli_mi,
    referans_yeniden_istenebilir_mi,
)
from app.agents.kart_duzenleme import (
    degisen_alanlar,
    dogrulama_sifirlanmali_mi,
    versiyon_artmali_mi,
    yeniden_eslestirme_gerekir_mi,
)
from app.api.auth import hesap_olustur
from app.core.kimlik import token_uret
from app.db.base import EMBEDDING_DIM
from app.models.eslesme import Eslesme
from app.models.guven_skoru import GuvenSkoru
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.models.referans_istegi import ReferansIstegi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler.dogrulama import ucuncu_taraf_puani
from tests.kanit_yardimcisi import link_parcasi
from tests.sahte_hesap import GENC_KAYIT_EKI
from tests.veritabani import api_istemcisi, geri_alinan_oturum

SIMDI = dt.datetime(2026, 9, 28, 12, tzinfo=dt.UTC)
VEKTOR = [1.0] + [0.0] * (EMBEDDING_DIM - 1)


# --- Saf kurallar ---------------------------------------------------------------------------


def test_degisen_alanlar_yalnizca_gercek_degisiklik():
    eski = {"baslik": "Kütüphane", "aciklama": None, "araclar": ["Python"]}
    assert degisen_alanlar(eski, {"baslik": "Kütüphane", "aciklama": ""}) == set()
    assert degisen_alanlar(eski, {"baslik": " Kütüphane "}) == set()
    assert degisen_alanlar(eski, {"aciklama": "Yeni"}) == {"aciklama"}
    assert degisen_alanlar(eski, {"araclar": ["Python", "Go"]}) == {"araclar"}
    assert not versiyon_artmali_mi(set())
    assert versiyon_artmali_mi({"aciklama"})


@pytest.mark.parametrize(
    ("degisenler", "sifirla"),
    [
        ({"aciklama"}, True),
        # Kanıt iddianın alanı değil: değişince gösterge yeniden değerlendirilir ama
        # iddia sıfırlanmaz, referanslar geçerli kalır (plan § 2; parcalar.py).
        ({"kanit_linki"}, False),
        ({"olculebilir_sonuc"}, True),
        ({"kendi_rolu"}, True),
        ({"baslik"}, True),
        ({"is_turu"}, False),  # etiket, iddia değil
        (set(), False),
    ],
)
def test_dogrulama_sifirlama_kurali(degisenler, sifirla):
    assert dogrulama_sifirlanmali_mi(degisenler) is sifirla


def test_referans_gecerliligi():
    once, sonra = SIMDI - dt.timedelta(days=1), SIMDI + dt.timedelta(hours=1)
    assert referans_gecerli_mi(once, None)  # içerik hiç değişmedi
    assert referans_gecerli_mi(None, None)  # eski satır, değişmedi
    assert not referans_gecerli_mi(once, SIMDI)  # değişiklikten önce
    assert not referans_gecerli_mi(None, SIMDI)  # tarihi bilinmeyen eski yanıt
    assert referans_gecerli_mi(sonra, SIMDI)
    yanitlar = [ReferansYaniti(5, once), ReferansYaniti(4, sonra), ReferansYaniti(None, None)]
    assert [y.puan for y in gecerli_referans_yanitlari(yanitlar, SIMDI)] == [4]
    assert [y.puan for y in gecerli_referans_yanitlari(yanitlar, None)] == [5, 4]


def test_yeniden_eslestirme_yalnizca_filtre_alaninda():
    assert yeniden_eslestirme_gerekir_mi({"sehir"})
    assert yeniden_eslestirme_gerekir_mi({"okul", "musaitlikler"})
    assert not yeniden_eslestirme_gerekir_mi({"okul", "github_url", "kariyer_durumu"})


@pytest.mark.parametrize(
    ("durum", "guncel", "bekleyen", "izinli"),
    [
        (DURUM_YANITLANDI, False, False, True),  # iş değişti: yeniden istenebilir
        (DURUM_YANIT_YOK, True, False, True),  # süresi doldu
        (DURUM_YANITLANDI, True, False, False),  # güncel yanıt zaten var
        (DURUM_BEKLIYOR, True, False, False),
        (DURUM_YANITLANDI, False, True, False),  # aynı kişiden yenisi bekleniyor
    ],
)
def test_referans_yeniden_istenebilir_mi(durum, guncel, bekleyen, izinli):
    engel = referans_yeniden_istenebilir_mi(
        durum=durum, guncel=guncel, ayni_kisiden_bekleyen_var=bekleyen
    )
    assert (engel is None) is izinli


# --- Gerçek veritabanında -------------------------------------------------------------------


def _email() -> str:
    return f"test-{uuid.uuid4().hex[:10]}@ornek.com"


def _skor():
    return GuvenSkoru(
        kanit_orijinalligi=3,
        sonuc_olculebilirligi=3,
        rol_netligi=3,
        ucuncu_taraf_onayi=3,
        gerekce_metni="g",
    )


async def _genc_ve_kart(oturum):
    hesap = await hesap_olustur(
        oturum, email=_email(), sifre="yeterince-uzun", rol="genc", ad="Elif"
    )
    kullanici = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
    a = SomutCikti(
        baslik="Kütüphane",
        aciklama="Ödünç takibi",
        kanit_parcalari=[link_parcasi("https://github.com/elif/kutuphane")],
        guven_skoru=_skor(),
        referans_istekleri=[
            ReferansIstegi(
                referans_email="hoca@ornek.edu.tr",
                durum=DURUM_YANITLANDI,
                puan=5,
                yanit_tarihi=dt.datetime.now(dt.UTC) - dt.timedelta(days=1),
            )
        ],
    )
    b = SomutCikti(
        baslik="Kulüp sitesi",
        kanit_parcalari=[link_parcasi("https://kulup.org")],
        guven_skoru=_skor(),
    )
    kart = YetenekKarti(
        kullanici_id=kullanici.id,
        rol_alani="backend geliştirici",
        deneyim_seviyesi="orta",
        embedding=VEKTOR,
        somut_ciktilar=[a, b],
    )
    oturum.add(kart)
    await oturum.commit()
    return hesap, kullanici, kart, a, b


def _baslik(hesap) -> dict:
    return {"Authorization": f"Bearer {token_uret(hesap.id, hesap.rol)}"}


async def _ciktiyi_oku(oturum, cikti_id):
    return await oturum.scalar(
        select(SomutCikti)
        .options(selectinload(SomutCikti.guven_skoru), selectinload(SomutCikti.referans_istekleri))
        .where(SomutCikti.id == cikti_id)
        .execution_options(populate_existing=True)
    )


def test_icerik_degisen_kalem_sifirlanir_digeri_korunur(kart_hazirlama_arka_plani_yok):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap, _, kart, a, b = await _genc_ve_kart(oturum)
            # Başlık bir kez: uçtaki geri alma paylaşılan oturumdaki nesneleri eskitiyor.
            baslik = _baslik(hesap)
            kart_id, a_id, b_id = kart.id, a.id, b.id
            yol = f"/yetenek-kartlari/{kart_id}/ciktilar"

            yanit = await istemci.patch(
                f"{yol}/{a_id}", headers=baslik, json={"aciklama": "Ödünç takibi, 3 şube"}
            )
            assert yanit.status_code == 200
            assert yanit.json()["versiyon"] == 2
            a_sonra, b_sonra = await _ciktiyi_oku(oturum, a_id), await _ciktiyi_oku(oturum, b_id)
            assert a_sonra.guven_skoru is None  # sıfırlandı, yeniden puanlanacak
            assert a_sonra.icerik_tarihi is not None
            assert b_sonra.guven_skoru is not None  # değişmedi, korundu
            # Eski referans yanıtı silinmedi ama artık puana girmiyor.
            assert len(a_sonra.referans_istekleri) == 1
            assert ucuncu_taraf_puani(a_sonra) is None  # eski yanıt geçmişte: "—"
            assert kart_hazirlama_arka_plani_yok == [(kart_id, 2, True)]

            # Yalnızca tür: gösterge korunur, versiyon yine artar.
            yanit = await istemci.patch(
                f"{yol}/{b_id}", headers=baslik, json={"is_turu": "gonulluluk"}
            )
            assert yanit.json()["versiyon"] == 3
            assert (await _ciktiyi_oku(oturum, b_id)).guven_skoru is not None

            # Aynı değer: hiçbir şey olmaz.
            yanit = await istemci.patch(
                f"{yol}/{b_id}", headers=baslik, json={"is_turu": "gonulluluk"}
            )
            assert yanit.json()["versiyon"] == 3
            assert len(kart_hazirlama_arka_plani_yok) == 2

            # Kanıt durumu eski yanıtı "güncel değil" diye gösterir.
            durum = (await istemci.get(f"/dogrulama/kalem/{a_id}", headers=baslik)).json()
            assert [r["guncel"] for r in durum["referanslar"]] == [False]

    asyncio.run(senaryo())


def test_referans_yeniden_istenir_ve_yeni_yanit_sayilir(kart_hazirlama_arka_plani_yok):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap, _, kart, a, _ = await _genc_ve_kart(oturum)
            # İddia değişti: eski referans yanıtı geçmişte kalır (karar 8).
            await istemci.patch(
                f"/yetenek-kartlari/{kart.id}/ciktilar/{a.id}",
                headers=_baslik(hesap),
                json={"aciklama": "Ödünç takibi ve geç iade hatırlatması"},
            )
            eski = (await _ciktiyi_oku(oturum, a.id)).referans_istekleri[0]

            ilk = await istemci.post(
                "/dogrulama/referans-yeniden-iste",
                headers=_baslik(hesap),
                json={"referans_id": str(eski.id)},
            )
            assert ilk.status_code == 201
            ikinci = await istemci.post(
                "/dogrulama/referans-yeniden-iste",
                headers=_baslik(hesap),
                json={"referans_id": str(eski.id)},
            )
            assert ikinci.status_code == 409  # aynı kişiden yanıt zaten bekleniyor

            yeni = next(
                r for r in (await _ciktiyi_oku(oturum, a.id)).referans_istekleri if r.id != eski.id
            )
            yanit = await istemci.post(
                "/dogrulama/referans-yaniti",
                json={"token": yeni.token, "iliski": "yonetici", "iddia_dogru": "kismen"},
            )
            assert yanit.status_code == 200
            # Yalnızca değişiklikten sonraki yanıt: kısmen → 1 (eski 5 sayılmaz).
            a_sonra = await _ciktiyi_oku(oturum, a.id)
            assert ucuncu_taraf_puani(a_sonra) == 1

    asyncio.run(senaryo())


def test_kart_alanlari_ve_is_kalemi_ekle_sil(kart_hazirlama_arka_plani_yok):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap, _, kart, a, b = await _genc_ve_kart(oturum)
            baslik = _baslik(hesap)
            yanit = await istemci.patch(
                f"/yetenek-kartlari/{kart.id}",
                headers=baslik,
                json={"araclar_teknolojiler": ["Python", "FastAPI"], "diller": ["İngilizce"]},
            )
            assert yanit.json()["araclar_teknolojiler"] == ["Python", "FastAPI"]
            assert yanit.json()["versiyon"] == 2

            eklenen = await istemci.post(
                f"/yetenek-kartlari/{kart.id}/ciktilar",
                headers=baslik,
                json={"baslik": "Hackathon botu", "is_turu": "yarisma"},
            )
            assert eklenen.status_code == 201
            assert len(eklenen.json()["somut_ciktilar"]) == 3
            assert eklenen.json()["kanit_bekleyen"] is True  # linksiz kalem eklendi

            for cikti_id in [a.id, b.id, eklenen.json()["somut_ciktilar"][-1]["id"]]:
                son = await istemci.delete(
                    f"/yetenek-kartlari/{kart.id}/ciktilar/{cikti_id}", headers=baslik
                )
            assert son.json()["somut_ciktilar"] == []
            assert son.json()["deneyim_seviyesi"] == "potansiyel"  # Keşif'teki kural
            assert son.json()["versiyon"] == 6

            # Ters yön: potansiyel karta çalışma eklenince seviye "başlangıç" olur.
            yeniden = await istemci.post(
                f"/yetenek-kartlari/{kart.id}/ciktilar",
                headers=baslik,
                json={"baslik": "Kulüp web sitesi"},
            )
            assert yeniden.json()["deneyim_seviyesi"] == "baslangic"

    asyncio.run(senaryo())


def test_duzenleme_yalnizca_onerildi_gerekcesini_bosaltir(kart_hazirlama_arka_plani_yok):
    """Kararı verilmiş kayıtlara dokunulmaz (plan § 0, karar 14)."""

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap, _, kart, a, _ = await _genc_ve_kart(oturum)
            kurum = Kurum(ad="Koop")
            oturum.add(kurum)
            await oturum.flush()
            kayitlar = {}
            for durum in ("onerildi", "genc_ilgilendi", "kabul_edildi"):
                ihtiyac = IhtiyacKarti(kurum_id=kurum.id, problem_tanimi="p", embedding=VEKTOR)
                oturum.add(ihtiyac)
                await oturum.flush()
                eslesme = Eslesme(
                    ihtiyac_karti_id=ihtiyac.id,
                    yetenek_karti_id=kart.id,
                    skor=0.8,
                    durum=durum,
                    gerekce_metni="eski gerekçe",
                )
                oturum.add(eslesme)
                kayitlar[durum] = eslesme
            await oturum.commit()

            await istemci.patch(
                f"/yetenek-kartlari/{kart.id}/ciktilar/{a.id}",
                headers=_baslik(hesap),
                json={"aciklama": "Tamamen farklı bir iş"},
            )
            for durum, eslesme in kayitlar.items():
                await oturum.refresh(eslesme)
                beklenen = None if durum == "onerildi" else "eski gerekçe"
                assert eslesme.gerekce_metni == beklenen, durum

    asyncio.run(senaryo())


def test_duzenleme_yetkisi():
    """401 token yok, 403 genç değil, 404 başkasının kartı ya da iş kalemi."""

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            _, _, kart, a, _ = await _genc_ve_kart(oturum)
            baska_genc, _, _, baska_cikti, _ = await _genc_ve_kart(oturum)
            kurum = await hesap_olustur(
                oturum, email=_email(), sifre="yeterince-uzun", rol="kurum", ad="Koop"
            )
            kart_yolu = f"/yetenek-kartlari/{kart.id}"
            cikti_yolu = f"{kart_yolu}/ciktilar/{a.id}"
            govde = {"aciklama": "x"}

            assert (await istemci.patch(cikti_yolu, json=govde)).status_code == 401
            assert (
                await istemci.patch(cikti_yolu, headers=_baslik(kurum), json=govde)
            ).status_code == 403
            assert (
                await istemci.patch(cikti_yolu, headers=_baslik(baska_genc), json=govde)
            ).status_code == 404
            assert (
                await istemci.patch(kart_yolu, headers=_baslik(baska_genc), json={"diller": []})
            ).status_code == 404
            assert (
                await istemci.delete(cikti_yolu, headers=_baslik(baska_genc))
            ).status_code == 404
            # Kendi kartının yolunda başkasının iş kalemi de 404.
            sahip = (
                await oturum.scalar(select(Kullanici).where(Kullanici.id == kart.kullanici_id))
            ).hesap_id
            sahip_basligi = {"Authorization": f"Bearer {token_uret(sahip, 'genc')}"}
            assert (
                await istemci.patch(
                    f"{kart_yolu}/ciktilar/{baska_cikti.id}", headers=sahip_basligi, json=govde
                )
            ).status_code == 404

    asyncio.run(senaryo())


def test_profilde_filtre_alani_degisince_kartlar_yeniden_eslesir(kart_hazirlama_arka_plani_yok):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            kayit = await istemci.post(
                "/auth/kayit",
                json={
                    "email": _email(),
                    "sifre": "yeterince-uzun",
                    "rol": "genc",
                    "ad": "Elif",
                    **GENC_KAYIT_EKI,
                },
            )
            baslik = {"Authorization": f"Bearer {kayit.json()['token']}"}
            kullanici = await oturum.scalar(
                select(Kullanici).where(Kullanici.hesap_id == uuid.UUID(kayit.json()["hesap_id"]))
            )
            kart = YetenekKarti(
                kullanici_id=kullanici.id, rol_alani="r", deneyim_seviyesi="orta", embedding=VEKTOR
            )
            oturum.add(kart)
            await oturum.commit()

            await istemci.patch("/profil", headers=baslik, json={"okul": "ODTÜ"})
            assert kart_hazirlama_arka_plani_yok == []  # filtreyi etkilemiyor

            await istemci.patch("/profil", headers=baslik, json={"musaitlikler": ["staj"]})
            assert kart_hazirlama_arka_plani_yok == [(kart.id, 1, False)]

    asyncio.run(senaryo())
