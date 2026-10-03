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

from app.agents.dogrulama import DURUM_YANITLANDI
from app.agents.dogrulama.cikarim import KanitCikarimi
from app.agents.dogrulama.kurallar import OkunanKanit
from app.api.auth import hesap_olustur
from app.core.kanit_okuma.belge import ErisimDurumu, KaynakSeviyesi, SahiplikKaynagi
from app.core.kimlik import token_uret
from app.models.bagli_hesap import BagliHesap
from app.models.inceleme_isareti import IncelemeIsareti
from app.models.kullanici import Kullanici
from app.models.referans_istegi import ReferansIstegi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler.dogrulama import kanit as kanit_servisi
from tests.kanit_yardimcisi import link_parcasi
from tests.veritabani import api_istemcisi, geri_alinan_oturum


@pytest.fixture
def sahte_degerlendirme(monkeypatch):
    """Link kontrolü ve model çıkarımı sahte; çıkarımın okuduğu kanıt adresi kaydedilir."""
    okunan: list[str | None] = []

    async def oku(url, _sorgular, **_):
        return OkunanKanit(
            erisim=ErisimDurumu.ACIK,
            seviye=KaynakSeviyesi.KAMUYA_ACIK,
            metin="Proje sayfası",
            url=url,
        )

    async def cikar(alanlar):
        okunan.append(alanlar["kanit_adresi"])
        return KanitCikarimi(
            ilgili_mi=True,
            sonuc_var=True,
            sonuc_sayisal=True,
            sonuc_olcut_acik=True,
            pay_var=True,
            pay_ozgul=True,
        )

    monkeypatch.setattr(kanit_servisi, "kanit_oku", oku)
    monkeypatch.setattr(kanit_servisi, "cikar", cikar)
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


def test_son_linki_kaldirmak_kaniti_bosaltir_referansi_korur(
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
            # Kanıt kalmadı: Kanıt "—", Sonuç ve Rol iddiayla (beyan tavanı 2), karar 10.
            assert skor["kanit_orijinalligi"] is None
            assert (skor["sonuc_olculebilirligi"], skor["rol_netligi"]) == (2, 2)
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
            # Her parça okunur; kaldırılınca yalnızca kalan link okunur.
            assert sahte_degerlendirme == [
                "https://ilk.org/proje",
                "https://ikinci.org/demo",
                "https://ikinci.org/demo",
            ]

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


def test_linksiz_kalem_degerlendirilir_ayni_girdi_modeli_yeniden_cagirmaz(
    sahte_degerlendirme, kart_hazirlama_arka_plani_yok
):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(oturum)
            yol = f"/dogrulama/kalem/{kalem_id}/degerlendir"
            ilk = await istemci.post(yol, headers=baslik)
            assert ilk.status_code == 200
            skor = ilk.json()["guven_skoru"]
            assert (skor["kanit_orijinalligi"], skor["sonuc_olculebilirligi"]) == (None, 2)
            assert skor["gerekce_metni"].startswith("Kanıt: Henüz kanıt eklemedin.")

            await istemci.post(yol, headers=baslik)  # aynı girdi: önbellek
            assert sahte_degerlendirme == ["(kanıt yok)"]

    asyncio.run(senaryo())


def test_itiraz_notu_zorunlu_ve_hakki_sinirli(sahte_degerlendirme, kart_hazirlama_arka_plani_yok):
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(oturum)
            yol = f"/dogrulama/kalem/{kalem_id}/itiraz"
            assert (await istemci.post(yol, headers=baslik, json={})).status_code == 422

            notlar = ["rolüm yazıyor", "sonuç sayılı", "linkte adım var"]
            for not_ in notlar:
                assert (
                    await istemci.post(yol, headers=baslik, json={"aciklama": not_})
                ).status_code == 200
            # Aynı not önbellekten döner, hak harcamaz.
            tekrar = await istemci.post(yol, headers=baslik, json={"aciklama": notlar[-1]})
            assert tekrar.status_code == 200
            assert tekrar.json()["inceleme_bekliyor"] is False
            # Dördüncü ve beşinci itiraz model çağırmaz; GİRVAK kuyruğunda tek işarette birikir.
            for not_ in ("başka not", "bir not daha"):
                yanit = await istemci.post(yol, headers=baslik, json={"aciklama": not_})
                assert yanit.status_code == 202
                assert yanit.json()["inceleme_bekliyor"] is True
            assert len(sahte_degerlendirme) == 3
            (isaret,) = (
                await oturum.scalars(
                    select(IncelemeIsareti).where(IncelemeIsareti.somut_cikti_id == kalem_id)
                )
            ).all()
            assert isaret.tur == "itiraz_siniri"
            assert isaret.ayrinti == {"itiraz_notlari": ["başka not", "bir not daha"]}

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


def test_bagli_hesap_okumaya_gider_ve_parcaya_yazilir(
    monkeypatch, sahte_degerlendirme, kart_hazirlama_arka_plani_yok
):
    """Servis gencin bağlı hesaplarını okumaya verir; seviye ve sahiplik parçaya yazılır."""
    gelen: list = []

    async def oku(url, _sorgular, *, bagli_hesaplar=(), **_):
        gelen.extend(bagli_hesaplar)
        return OkunanKanit(
            erisim=ErisimDurumu.ACIK,
            seviye=KaynakSeviyesi.PLATFORM,
            metin="Proje sayfası",
            url=url,
            platform="github",
            sahiplik_kaynagi=SahiplikKaynagi.OAUTH,
        )

    monkeypatch.setattr(kanit_servisi, "kanit_oku", oku)

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _kart_id, kalem_id = await _genc_ve_kalem(oturum)
            kart = await oturum.get(YetenekKarti, _kart_id)
            oturum.add(
                BagliHesap(
                    kullanici_id=kart.kullanici_id,
                    saglayici="github",
                    kullanici_adi="elif",
                    dis_kimlik="42",
                    yontem="oauth",
                )
            )
            await oturum.commit()
            yanit = await istemci.post(
                f"/dogrulama/kalem/{kalem_id}/kanit",
                headers=baslik,
                json={"url": "github.com/elif/kutuphane"},
            )
            assert yanit.status_code == 201
            assert yanit.json()["guven_skoru"]["kanit_orijinalligi"] == 3
            assert [(h.saglayici, h.kullanici_adi, h.dis_kimlik) for h in gelen] == [
                ("github", "elif", "42")
            ]
            parca = (await _kalemi_oku(oturum, kalem_id)).kanit_parcalari[0]
            assert (parca.seviye, parca.sahiplik_kaynagi, parca.platform) == (
                "platform",
                "oauth",
                "github",
            )

    asyncio.run(senaryo())
