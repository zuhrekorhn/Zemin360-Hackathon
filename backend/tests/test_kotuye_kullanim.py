"""Kötüye kullanım işaretleri (plan § 9, adım 11): sinyal GİRVAK kuyruğuna düşer,
puan değişmez (İ1); aynı sinyal bir kez düşer."""

import asyncio
import io

import pytest
from PIL import Image, ImageDraw
from sqlalchemy import select

from app.core import gorsel_ozeti
from app.models.inceleme_isareti import TUR_AYNI_IDDIA_COK_HESAPTA, IncelemeIsareti
from app.servisler.dogrulama.isaretler.tekrar import takim_projesi_mi
from tests.test_kanit_parcasi import _genc_ve_kalem, _kalemi_oku, sahte_degerlendirme  # noqa: F401
from tests.veritabani import api_istemcisi, geri_alinan_oturum

LINK = "https://github.com/ornek/kutuphane"


def _desenli(bicim="PNG", *, boyut=(256, 256), kaydir=0, kalite=95) -> bytes:
    """Düz renk değil, desenli görsel (algısal özet düz renkte anlamsız)."""
    resim = Image.new("RGB", boyut, (240, 240, 240))
    ciz = ImageDraw.Draw(resim)
    w, h = boyut
    ciz.ellipse((w // 8 + kaydir, h // 8, w // 2 + kaydir, h // 2), fill=(200, 30, 30))
    ciz.rectangle((w // 2, h // 2, w - w // 8, h - h // 8), fill=(20, 40, 160))
    ciz.line((0, h - 1, w - 1, 0), fill=(0, 0, 0), width=max(1, w // 40))
    cikti = io.BytesIO()
    resim.save(cikti, format=bicim, **({"quality": kalite} if bicim == "JPEG" else {}))
    return cikti.getvalue()


def _baska_desen() -> bytes:
    resim = Image.new("RGB", (256, 256), (10, 10, 10))
    ciz = ImageDraw.Draw(resim)
    for i in range(0, 256, 32):
        ciz.rectangle((i, 0, i + 15, 255), fill=(250, 250, 0))
    cikti = io.BytesIO()
    resim.save(cikti, format="PNG")
    return cikti.getvalue()


# --- Saf: algısal özet ve takım projesi ---------------------------------------------------


def test_algisal_ozet_yeniden_kodlamaya_ve_boyuta_dayanikli():
    asil = gorsel_ozeti.algisal_ozet(_desenli())
    assert asil is not None and len(asil) == 16
    kopya = gorsel_ozeti.algisal_ozet(_desenli("JPEG", boyut=(180, 180), kalite=70))
    assert gorsel_ozeti.benzer_mi(asil, kopya)
    assert not gorsel_ozeti.benzer_mi(asil, gorsel_ozeti.algisal_ozet(_baska_desen()))
    assert not gorsel_ozeti.benzer_mi(asil, None)
    assert gorsel_ozeti.algisal_ozet(b"gorsel degil") is None


def test_takim_projesi_iki_tarafin_da_katkici_listesiyle_dogrulanmasi():
    assert takim_projesi_mi("oauth", "oauth")
    assert not takim_projesi_mi("oauth", "yok")
    assert not takim_projesi_mi("profil_kodu", "oauth")
    assert not takim_projesi_mi(None, None)


# --- Uçtan: aynı iddia başka hesapta -------------------------------------------------------


async def _isaretler(oturum, tur, kalem_idleri):
    return list(
        await oturum.scalars(
            select(IncelemeIsareti).where(
                IncelemeIsareti.tur == tur, IncelemeIsareti.somut_cikti_id.in_(kalem_idleri)
            )
        )
    )


@pytest.mark.usefixtures("sahte_degerlendirme")
def test_ayni_link_ikinci_hesapta_isaret_ve_karar_sonrasi_tekrar_acilmaz():
    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            b1, _, k1 = await _genc_ve_kalem(oturum)
            yanit = await istemci.post(
                f"/dogrulama/kalem/{k1}/kanit", headers=b1, json={"url": LINK}
            )
            assert yanit.status_code == 201, yanit.text
            assert await _isaretler(oturum, TUR_AYNI_IDDIA_COK_HESAPTA, [k1]) == []

            b2, _, k2 = await _genc_ve_kalem(oturum)
            yanit = await istemci.post(
                f"/dogrulama/kalem/{k2}/kanit", headers=b2, json={"url": LINK + "/"}
            )
            assert yanit.status_code == 201, yanit.text
            # Puan değişmedi (İ1): sahte değerlendirmenin puanı
            assert yanit.json()["guven_skoru"]["kanit_orijinalligi"] == 2
            [isaret] = await _isaretler(oturum, TUR_AYNI_IDDIA_COK_HESAPTA, [k1, k2])
            assert isaret.somut_cikti_id == k2
            [eslesme] = isaret.ayrinti["eslesmeler"]
            assert eslesme["neden"] == "adres"
            assert eslesme["adres"] == LINK + "/"

            # GİRVAK "sorun yok" dedi: yeniden değerlendirme aynı eşleşmeyi geri getirmez.
            isaret.durum = "kapandi"
            await oturum.commit()
            kalem = await _kalemi_oku(oturum, k2)
            kalem.guven_skoru.girdi_ozeti = None  # önbelleği atla
            await oturum.commit()
            yanit = await istemci.post(f"/dogrulama/kalem/{k2}/degerlendir", headers=b2)
            assert yanit.status_code == 200, yanit.text
            assert len(await _isaretler(oturum, TUR_AYNI_IDDIA_COK_HESAPTA, [k2])) == 1

    asyncio.run(senaryo())


@pytest.mark.usefixtures("sahte_degerlendirme", "dosya_modele_okutulmaz", "depo")
def test_ayni_dosya_ve_benzer_gorsel_baska_hesapta():
    def yukle(istemci, kalem_id, baslik, ham, ad):
        return istemci.post(
            f"/dogrulama/kalem/{kalem_id}/dosya", headers=baslik, files={"dosya": (ad, ham)}
        )

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            b1, _, k1 = await _genc_ve_kalem(oturum)
            assert (await yukle(istemci, k1, b1, _desenli(), "a.png")).status_code == 201
            assert (await yukle(istemci, k1, b1, ornek_pdf := _pdf(), "r.pdf")).status_code == 201

            b2, _, k2 = await _genc_ve_kalem(oturum)
            # Aynı PDF (aynı özet) ve yeniden kaydedilmiş görsel (başka özet, benzer görünüş)
            assert (await yukle(istemci, k2, b2, ornek_pdf, "kopya.pdf")).status_code == 201
            benzer = _desenli("JPEG", boyut=(200, 200), kalite=80)
            assert (await yukle(istemci, k2, b2, benzer, "b.jpg")).status_code == 201
            # Başka bir görsel eşleşmez
            assert (await yukle(istemci, k2, b2, _baska_desen(), "c.png")).status_code == 201

            [isaret] = await _isaretler(oturum, TUR_AYNI_IDDIA_COK_HESAPTA, [k1, k2])
            nedenler = sorted(e["neden"] for e in isaret.ayrinti["eslesmeler"])
            assert nedenler == ["dosya", "gorsel"]
            adlar = {e["neden"]: e["dosya_adi"] for e in isaret.ayrinti["eslesmeler"]}
            assert adlar == {"dosya": "kopya.pdf", "gorsel": "b.jpg"}

    asyncio.run(senaryo())


def _pdf() -> bytes:
    from tests import dosya_ornekleri

    return dosya_ornekleri.metinli_pdf(["Proje raporu", "Kutuphane takip sistemi"])


# --- Görsel başka bir sayfada (Cloud Vision, kapalı bayrak) ---------------------------------


def test_gorsel_alani_rol_alanindan_ve_araclardan():
    from app.agents.dogrulama.gorsel_kaynagi import gorsel_alani_mi

    assert gorsel_alani_mi("UI/UX Tasarımcı")
    assert gorsel_alani_mi("Fotoğrafçı")
    assert gorsel_alani_mi("Grafik tasarım")
    assert gorsel_alani_mi("Frontend geliştirici", ["React", "Figma"])
    assert not gorsel_alani_mi("Backend geliştirici", ["Python", "PostgreSQL"])
    assert not gorsel_alani_mi("Veri analisti (Quartz)")  # "art" kelime başı değil
    assert not gorsel_alani_mi(None)


def test_baskasindaki_sayfalar_yalnizca_birebir_ve_baskasinin():
    from app.agents.dogrulama.gorsel_kaynagi import baskasindaki_sayfalar
    from app.agents.dogrulama.hesap_sahipligi import BagliHesapBilgisi
    from app.core.dis_servisler.gorsel_arayici import EslesenSayfa

    sayfalar = [
        EslesenSayfa("https://www.behance.net/baskasi/proje", "Afiş", True),
        EslesenSayfa("https://www.behance.net/elif/afis", "Afişim", True),
        EslesenSayfa("https://dribbble.com/elifd", "Dribbble", True),
        EslesenSayfa("https://stok.example.com/doku", None, False),
    ]
    bagli = [BagliHesapBilgisi("dribbble", "ElifD", "profil_kodu")]
    sonuc = baskasindaki_sayfalar(sayfalar, bagli, ["https://behance.net/elif"])
    assert [s.adres for s in sonuc] == ["https://www.behance.net/baskasi/proje"]


def test_cloud_vision_istegi_ve_yaniti():
    import httpx

    from app.core.dis_servisler.gorsel_arayici import CloudVisionArayici

    giden = {}

    def isle(istek: httpx.Request) -> httpx.Response:
        import json

        giden["anahtar"] = istek.headers.get("x-goog-api-key")
        giden["adres"] = str(istek.url)
        giden["govde"] = json.loads(istek.content)
        return httpx.Response(
            200,
            json={
                "responses": [
                    {
                        "webDetection": {
                            "pagesWithMatchingImages": [
                                {
                                    "url": "https://ornek.com/a",
                                    "pageTitle": "<b>Afiş</b>",
                                    "fullMatchingImages": [{"url": "https://ornek.com/a.png"}],
                                },
                                {"url": "https://ornek.com/b", "partialMatchingImages": [{}]},
                                {"url": "javascript:alert(1)", "fullMatchingImages": [{}]},
                            ]
                        }
                    }
                ]
            },
        )

    arayici = CloudVisionArayici("gizli", 5, transport=httpx.MockTransport(isle))
    sonuc = asyncio.run(arayici.ara(_desenli(boyut=(2000, 1500))))
    assert giden["anahtar"] == "gizli" and "gizli" not in giden["adres"]
    istek = giden["govde"]["requests"][0]
    assert istek["features"][0]["type"] == "WEB_DETECTION"
    gonderilen = Image.open(io.BytesIO(__import__("base64").b64decode(istek["image"]["content"])))
    assert max(gonderilen.size) == 1024
    assert [(s.adres, s.tam_eslesme) for s in sonuc.sayfalar] == [
        ("https://ornek.com/a", True),
        ("https://ornek.com/b", False),
    ]

    yasak = httpx.MockTransport(lambda _: httpx.Response(403))
    hatali = CloudVisionArayici("x", 5, transport=yasak)
    assert asyncio.run(hatali.ara(_desenli())) is None


def test_aylik_tavan_kalici_sayacla():
    from app.servisler import servis_kullanimi

    async def senaryo():
        async with geri_alinan_oturum() as oturum:
            servis = "deneme_servisi"
            assert await servis_kullanimi.hak_al(oturum, servis, 2)
            assert await servis_kullanimi.hak_al(oturum, servis, 2)
            assert not await servis_kullanimi.hak_al(oturum, servis, 2)
            assert not await servis_kullanimi.hak_al(oturum, "baska", 0)

    asyncio.run(senaryo())


class _SahteArayici:
    kip = "sahte"

    def __init__(self, sayfalar):
        self.sayfalar = sayfalar
        self.cagri = 0

    async def ara(self, veri):
        from app.core.dis_servisler.gorsel_arayici import AramaSonucu

        self.cagri += 1
        return AramaSonucu(tuple(self.sayfalar))


@pytest.mark.usefixtures("sahte_degerlendirme", "dosya_modele_okutulmaz", "depo")
def test_tasarimcinin_gorseli_baska_portfolyoda_isaret(monkeypatch):
    from app.core.dis_servisler import kurulum
    from app.core.dis_servisler.gorsel_arayici import EslesenSayfa
    from app.models.inceleme_isareti import TUR_GORSEL_BASKASINDA
    from app.models.yetenek_karti import YetenekKarti

    arayici = _SahteArayici(
        [
            EslesenSayfa("https://www.behance.net/baskasi/afis", "Afiş", True),
            EslesenSayfa("https://www.behance.net/elif/afis", "Afişim", True),
        ]
    )
    monkeypatch.setattr(kurulum, "gorsel_arayici", lambda: arayici)

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            # Yazılımcının görseli aranmaz (alan dışında)
            b0, _, k0 = await _genc_ve_kalem(oturum)
            yanit = await istemci.post(
                f"/dogrulama/kalem/{k0}/dosya", headers=b0, files={"dosya": ("a.png", _desenli())}
            )
            assert yanit.status_code == 201, yanit.text
            assert arayici.cagri == 0

            b1, kart_id, k1 = await _genc_ve_kalem(oturum, link="https://behance.net/elif/x")
            kart = await oturum.get(YetenekKarti, kart_id)
            kart.rol_alani = "Grafik tasarımcı"
            await oturum.commit()
            yanit = await istemci.post(
                f"/dogrulama/kalem/{k1}/dosya",
                headers=b1,
                files={"dosya": ("afis.png", _baska_desen())},
            )
            assert yanit.status_code == 201, yanit.text
            assert yanit.json()["guven_skoru"] is not None  # akış sürdü, puan sinyalden bağımsız
            assert arayici.cagri == 1
            [isaret] = await _isaretler(oturum, TUR_GORSEL_BASKASINDA, [k1])
            [sayfa] = isaret.ayrinti["sayfalar"]
            assert sayfa["adres"] == "https://www.behance.net/baskasi/afis"
            assert sayfa["dosya_adi"] == "afis.png"
            kalem = await _kalemi_oku(oturum, k1)
            [gorsel] = [p for p in kalem.kanit_parcalari if p.tur == "gorsel"]
            assert gorsel.belge["kaynak_aramasi"]["tam_eslesen_sayfa"] == 2

    asyncio.run(senaryo())
