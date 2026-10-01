"""Kanıt parçaları: tek kapı, gösterge ve referansın birbirine etkisi (gerçek veritabanı).

docs/plans/dogrulama-iyilestirme.md § 2 (kanıt eklemek puanı düşürmez), § 12
bulgu 16 (referans istemek yeniden değerlendirmez), 25 (link tek yoldan), 26
(gösterge değişince eşleşmeler tazelenir), 28 (kanıt bekliyor rozeti).
Link kontrolü ve rubrik sahte: ağ ve model çağrılmaz, rubrik çağrıları sayılır.
"""

import asyncio
import datetime as dt
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.dogrulama import DURUM_YANITLANDI, LinkKontrolu, RubrikPuani
from app.api.auth import hesap_olustur
from app.core.kimlik import token_uret
from app.models.kullanici import Kullanici
from app.models.referans_istegi import ReferansIstegi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler.dogrulama import kanit as kanit_servisi
from tests.kanit_yardimcisi import link_parcasi
from tests.veritabani import api_istemcisi, geri_alinan_oturum


@pytest.fixture
def sahte_degerlendirme(monkeypatch):
    """Link kontrolü ve rubrik sahte; rubrik çağrılarının okuduğu link kaydedilir."""
    okunan: list[str | None] = []

    async def link(adres):
        return LinkKontrolu(True, 200, "Proje sayfası", "açılıyor")

    async def rubrik(*, kanit_linki, **_):
        okunan.append(kanit_linki)
        return RubrikPuani(
            kanit_orijinalligi=2, sonuc_olculebilirligi=2, rol_netligi=3, gerekce_metni="not"
        )

    monkeypatch.setattr(kanit_servisi, "linki_kontrol_et", link)
    monkeypatch.setattr(kanit_servisi, "rubrik_puanla", rubrik)
    return okunan


async def _genc_ve_kalem(oturum, *, link: str | None = None, referans_yanitli: bool = False):
    hesap = await hesap_olustur(
        oturum,
        email=f"test-{uuid.uuid4().hex[:10]}@ornek.com",
        sifre="yeterince-uzun",
        rol="genc",
        ad="Elif",
    )
    kullanici = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
    referanslar = []
    if referans_yanitli:
        referanslar.append(
            ReferansIstegi(
                referans_email="hoca@ornek.edu.tr",
                durum=DURUM_YANITLANDI,
                puan=5,
                yanit_tarihi=dt.datetime.now(dt.UTC),
            )
        )
    kalem = SomutCikti(
        baslik="Kütüphane",
        aciklama="Ödünç takibi",
        kanit_parcalari=[link_parcasi(link)] if link else [],
        referans_istekleri=referanslar,
    )
    kart = YetenekKarti(
        kullanici_id=kullanici.id,
        rol_alani="backend geliştirici",
        deneyim_seviyesi="orta",
        somut_ciktilar=[kalem],
    )
    oturum.add(kart)
    await oturum.commit()
    baslik = {"Authorization": f"Bearer {token_uret(hesap.id, hesap.rol)}"}
    return baslik, kart.id, kalem.id


async def _kalemi_oku(oturum, kalem_id):
    return await oturum.scalar(
        select(SomutCikti)
        .options(
            selectinload(SomutCikti.guven_skoru),
            selectinload(SomutCikti.kanit_parcalari),
            selectinload(SomutCikti.referans_istekleri),
        )
        .where(SomutCikti.id == kalem_id)
        .execution_options(populate_existing=True)
    )


def test_kanit_eklemek_degerlendirir_ve_referansi_gecersiz_kilmaz(
    sahte_degerlendirme, kart_hazirlama_arka_plani_yok
):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, kart_id, kalem_id = await _genc_ve_kalem(oturum, referans_yanitli=True)
            yanit = await istemci.post(
                f"/dogrulama/kalem/{kalem_id}/kanit",
                headers=baslik,
                json={"url": "github.com/elif/kutuphane"},
            )
            assert yanit.status_code == 201
            govde = yanit.json()
            assert [k["url"] for k in govde["kanitlar"]] == ["github.com/elif/kutuphane"]
            assert govde["guven_skoru"]["kanit_orijinalligi"] == 2
            # Referans yanıtı geçerli kaldı: kanıt iddiayı değiştirmez (plan § 2).
            assert govde["guven_skoru"]["ucuncu_taraf_onayi"] == 3
            assert govde["kart_kanit_bekleyen"] is False

            kalem = await _kalemi_oku(oturum, kalem_id)
            assert kalem.icerik_tarihi is None
            assert kalem.guven_skoru.degerlendirme_tarihi is not None
            # Gösterge değişti: sürüm arttı, kart hazırlama sıraya girdi (bulgu 26).
            kart = await oturum.get(YetenekKarti, kart_id, populate_existing=True)
            assert kart.versiyon == 2
            assert kart_hazirlama_arka_plani_yok == [(kart_id, 2, False)]

    asyncio.run(senaryo())


def test_ayni_link_ikinci_kez_eklenemez(sahte_degerlendirme, kart_hazirlama_arka_plani_yok):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(
                oturum, link="https://github.com/elif/kutuphane"
            )
            # Aynı sayfanın başka yazımı (www, sondaki /, izleme parametresi)
            yanit = await istemci.post(
                f"/dogrulama/kalem/{kalem_id}/kanit",
                headers=baslik,
                json={"url": "http://www.github.com/elif/kutuphane/?utm_source=x"},
            )
            assert yanit.status_code == 409
            assert sahte_degerlendirme == []  # model çağrılmadı

    asyncio.run(senaryo())


def test_son_linki_kaldirmak_degerlendirmeyi_bosaltir_referansi_korur(
    sahte_degerlendirme, kart_hazirlama_arka_plani_yok
):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(oturum, referans_yanitli=True)
            eklendi = await istemci.post(
                f"/dogrulama/kalem/{kalem_id}/kanit",
                headers=baslik,
                json={"url": "https://github.com/elif/kutuphane"},
            )
            parca_id = eklendi.json()["kanitlar"][0]["id"]

            yanit = await istemci.delete(
                f"/dogrulama/kalem/{kalem_id}/kanit/{parca_id}", headers=baslik
            )
            assert yanit.status_code == 200
            skor = yanit.json()["guven_skoru"]
            assert (skor["kanit_orijinalligi"], skor["sonuc_olculebilirligi"]) == (None, None)
            assert skor["rol_netligi"] is None
            assert skor["ucuncu_taraf_onayi"] == 3  # referans korunur
            assert yanit.json()["kanitlar"] == []
            # Kanıt yok ama referans var: "kanıt bekliyor" değil.
            assert yanit.json()["kart_kanit_bekleyen"] is False

            yok = await istemci.delete(
                f"/dogrulama/kalem/{kalem_id}/kanit/{uuid.uuid4()}", headers=baslik
            )
            assert yok.status_code == 404

    asyncio.run(senaryo())


def test_kalan_link_ile_yeniden_degerlendirilir(sahte_degerlendirme, kart_hazirlama_arka_plani_yok):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(oturum, link="https://ilk.org/proje")
            ikinci = await istemci.post(
                f"/dogrulama/kalem/{kalem_id}/kanit",
                headers=baslik,
                json={"url": "https://ikinci.org/demo"},
            )
            ilk_id = next(
                k["id"] for k in ikinci.json()["kanitlar"] if k["url"] == "https://ilk.org/proje"
            )
            await istemci.delete(f"/dogrulama/kalem/{kalem_id}/kanit/{ilk_id}", headers=baslik)
            # Önce birincil link (ilk), kaldırılınca kalan link okundu.
            assert sahte_degerlendirme == ["https://ilk.org/proje", "https://ikinci.org/demo"]

    asyncio.run(senaryo())


def test_referans_istemek_degerlendirmez_ve_rozeti_gunceller(
    sahte_degerlendirme, kart_hazirlama_arka_plani_yok
):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, kart_id, kalem_id = await _genc_ve_kalem(oturum)
            await oturum.execute(
                YetenekKarti.__table__.update()
                .where(YetenekKarti.id == kart_id)
                .values(kanit_bekleyen=True)
            )
            await oturum.commit()

            yanit = await istemci.post(
                f"/dogrulama/kalem/{kalem_id}/referans",
                headers=baslik,
                json={"referans_email": "hoca@ornek.edu.tr"},
            )
            assert yanit.status_code == 201
            assert sahte_degerlendirme == []  # bulgu 16: model çağrılmadı
            assert yanit.json()["guven_skoru"] is None
            assert yanit.json()["kart_kanit_bekleyen"] is False  # bulgu 28
            assert kart_hazirlama_arka_plani_yok == []  # gösterge değişmedi

    asyncio.run(senaryo())


def test_kanitsiz_kalem_degerlendirilemez(sahte_degerlendirme, kart_hazirlama_arka_plani_yok):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(oturum)
            for yol, govde in (("degerlendir", None), ("itiraz", {"aciklama": "x"})):
                yanit = await istemci.post(
                    f"/dogrulama/kalem/{kalem_id}/{yol}", headers=baslik, json=govde
                )
                assert yanit.status_code == 409
            assert sahte_degerlendirme == []

    asyncio.run(senaryo())


def test_yeni_calisma_formundaki_link_parca_olur(kart_hazirlama_arka_plani_yok):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, kart_id, _ = await _genc_ve_kalem(oturum)
            yanit = await istemci.post(
                f"/yetenek-kartlari/{kart_id}/ciktilar",
                headers=baslik,
                json={"baslik": "Kulüp sitesi", "kanit_linki": "https://kulup.org"},
            )
            assert yanit.status_code == 201
            yeni = next(c for c in yanit.json()["somut_ciktilar"] if c["baslik"] == "Kulüp sitesi")
            assert [k["url"] for k in yeni["kanitlar"]] == ["https://kulup.org"]

            # İddia düzenleme formu link almaz (kanıt tek kapıdan, bulgu 25).
            duzenle = await istemci.patch(
                f"/yetenek-kartlari/{kart_id}/ciktilar/{yeni['id']}",
                headers=baslik,
                json={"kanit_linki": "https://baska.org"},
            )
            assert duzenle.status_code == 422

    asyncio.run(senaryo())
