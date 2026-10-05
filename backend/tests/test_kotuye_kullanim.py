"""Kötüye kullanım işaretleri (plan § 9, adım 11): sinyal GİRVAK kuyruğuna düşer,
puan değişmez (İ1); aynı sinyal bir kez düşer."""

import asyncio
import datetime as dt
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


# --- Şüpheli referans yanıtı -----------------------------------------------------------------


def test_referans_sinyalleri_kurali():
    from app.agents.dogrulama.referans_suphesi import referans_sinyalleri

    def sinyal(**ek):
        girdi = dict(
            yanit_ip="a",
            yanit_tarayici="t",
            genc_ipleri={"b"},
            genc_tarayicilari={"u"},
            form_acildi=True,
            form_suresi_sn=120.0,
            genc_sayisi=1,
        )
        return referans_sinyalleri(**{**girdi, **ek})

    assert sinyal() == ()
    assert sinyal(genc_ipleri={"a"}, genc_tarayicilari={"t"}) == (
        "ip_genc_ile_ayni",
        "tarayici_genc_ile_ayni",
    )
    assert sinyal(yanit_ip=None, genc_ipleri={None}) == ()
    assert sinyal(form_suresi_sn=8.0) == ("hizli_yanit",)
    assert sinyal(form_acildi=False, form_suresi_sn=None) == ("form_acilmadan",)
    assert sinyal(genc_sayisi=3) == ("cok_gence_yanit",)


def test_istek_izi_tuzlu_ozet_ve_yerel_adres():
    from starlette.requests import Request

    from app.core import istek_izi

    def istek(basliklar, istemci=("10.0.0.5", 1)):
        return Request(
            {
                "type": "http",
                "headers": [(k.lower().encode(), v.encode()) for k, v in basliklar.items()],
                "client": istemci,
            }
        )

    ua = {"User-Agent": "Tarayici/1.0", "Accept-Language": "tr"}
    iz = istek_izi.istekten(istek({**ua, "X-Forwarded-For": "9.9.9.9, 85.10.20.30"}))
    assert iz.ip == istek_izi.ozetle("ip:85.10.20.30") and "85.10" not in iz.ip
    assert iz.tarayici == istek_izi.istekten(istek(ua)).tarayici
    # Yerel / özel ağ adresinin özeti alınmaz (yerelde herkes aynı adrestir)
    assert istek_izi.istekten(istek(ua)).ip is None
    assert istek_izi.istekten(istek({})).tarayici is None


AYNI_AG = {"X-Forwarded-For": "85.10.20.30", "User-Agent": "Tarayici/1.0"}


async def _referans_isteyen_genc(oturum, istemci, referans_email=None):
    import uuid

    from app.models.referans_istegi import ReferansIstegi

    baslik, _, kalem_id = await _genc_ve_kalem(oturum)
    yanit = await istemci.post(
        f"/dogrulama/kalem/{kalem_id}/referans",
        headers={**baslik, **AYNI_AG},
        json={"referans_email": referans_email or f"hoca-{uuid.uuid4().hex[:8]}@ornek.edu.tr"},
    )
    assert yanit.status_code == 201, yanit.text
    istek = await oturum.scalar(
        select(ReferansIstegi)
        .where(ReferansIstegi.somut_cikti_id == kalem_id)
        .execution_options(populate_existing=True)
    )
    return kalem_id, istek


@pytest.mark.usefixtures("eposta_gonderilmez")
def test_genc_ile_ayni_agdan_hizli_yanit_isaret_acar():
    from app.models.inceleme_isareti import TUR_REFERANS_SUPHELI

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            kalem_id, istek = await _referans_isteyen_genc(oturum, istemci)
            assert istek.yanit_isareti["istek_izi"]["ip"]
            assert (await istemci.get(f"/dogrulama/referans/{istek.token}")).status_code == 200
            yanit = await istemci.post(
                "/dogrulama/referans-yaniti",
                headers=AYNI_AG,
                json={"token": istek.token, "iliski": "diger", "iddia_dogru": "evet"},
            )
            assert yanit.status_code == 200, yanit.text
            [isaret] = await _isaretler(oturum, TUR_REFERANS_SUPHELI, [kalem_id])
            [satir] = isaret.ayrinti["referanslar"]
            assert satir["sinyaller"] == [
                "ip_genc_ile_ayni",
                "tarayici_genc_ile_ayni",
                "hizli_yanit",
            ]
            assert "@" not in str(isaret.ayrinti)  # işarette e-posta yok
            await oturum.refresh(istek)
            assert istek.yanit_isareti["sinyaller"] == satir["sinyaller"]
            # Referans başlığı yanıttan hesaplandı: işaret puanı değiştirmez (İ1)
            durum = await istemci.get(
                f"/dogrulama/kalem/{kalem_id}",
                headers={"Authorization": (await _sahibin_basligi(oturum, kalem_id))},
            )
            assert durum.json()["guven_skoru"]["ucuncu_taraf_onayi"] == 3

    asyncio.run(senaryo())


async def _sahibin_basligi(oturum, kalem_id):
    from app.core.kimlik import token_uret
    from app.models.hesap import Hesap
    from app.models.kullanici import Kullanici
    from app.models.somut_cikti import SomutCikti
    from app.models.yetenek_karti import YetenekKarti

    hesap = await oturum.scalar(
        select(Hesap)
        .join(Kullanici, Kullanici.hesap_id == Hesap.id)
        .join(YetenekKarti, YetenekKarti.kullanici_id == Kullanici.id)
        .join(SomutCikti, SomutCikti.yetenek_karti_id == YetenekKarti.id)
        .where(SomutCikti.id == kalem_id)
    )
    return f"Bearer {token_uret(hesap.id, hesap.rol)}"


@pytest.mark.usefixtures("eposta_gonderilmez")
def test_cok_gence_yanit_ve_form_acilmadan():
    from app.models.inceleme_isareti import TUR_REFERANS_SUPHELI

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            import uuid

            kalemler = []
            ayni_kisi = f"Hoca-{uuid.uuid4().hex[:8]}@Ornek.edu.tr"
            for i in range(3):
                # Büyük / küçük harf farkı aynı kişiyi ayırmaz
                eposta = ayni_kisi if i % 2 else ayni_kisi.lower()
                kalem_id, istek = await _referans_isteyen_genc(oturum, istemci, eposta)
                kalemler.append(kalem_id)
                yanit = await istemci.post(
                    "/dogrulama/referans-yaniti",
                    headers={"X-Forwarded-For": "91.1.1.1", "User-Agent": "Baska/2"},
                    json={"token": istek.token, "iliski": "diger", "iddia_dogru": "evet"},
                )
                assert yanit.status_code == 200, yanit.text
            isaretler = await _isaretler(oturum, TUR_REFERANS_SUPHELI, kalemler)
            sinyaller = {
                i.somut_cikti_id: i.ayrinti["referanslar"][0]["sinyaller"] for i in isaretler
            }
            assert sinyaller[kalemler[0]] == ["form_acilmadan"]
            assert sinyaller[kalemler[2]] == ["form_acilmadan", "cok_gence_yanit"]

    asyncio.run(senaryo())


@pytest.mark.usefixtures("eposta_gonderilmez")
def test_izler_90_gun_sonra_silinir_sinyaller_kalir():
    import datetime as dt

    from app.servisler.dogrulama.isaretler.referans_suphesi import eski_izleri_temizle

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            _, istek = await _referans_isteyen_genc(oturum, istemci)
            istek.yanit_isareti = {**istek.yanit_isareti, "sinyaller": ["hizli_yanit"]}
            await oturum.commit()
            simdi = istek.olusturma_tarihi + dt.timedelta(days=89)
            assert await eski_izleri_temizle(oturum, simdi) == 0
            simdi = istek.olusturma_tarihi + dt.timedelta(days=91)
            assert await eski_izleri_temizle(oturum, simdi) >= 1
            assert istek.yanit_isareti == {"sinyaller": ["hizli_yanit"]}

    asyncio.run(senaryo())


# --- Belge tutarsız ve kanıt çelişiyor --------------------------------------------------------


@pytest.mark.parametrize(
    ("capa", "neden"),
    [
        ({"tur": "imza", "gecerli": False, "butun": False}, "bozuk_imza"),
        ({"tur": "imza", "gecerli": True, "butun": False}, "bozuk_imza"),
        ({"tur": "imza", "gecerli": True, "butun": True}, None),
        ({"tur": "adres", "okundu": True, "kaynak": "kod", "adres": "https://a"}, "ad_eslesmedi"),
        (
            {"tur": "adres", "okundu": True, "kaynak": "metin", "duzenleyen": "Credly"},
            "ad_eslesmedi",
        ),
        ({"tur": "adres", "okundu": True, "kaynak": "metin"}, None),  # tanınmayan adres
        ({"tur": "adres", "okundu": True, "kaynak": "kod", "ad_eslesti": True}, None),
        ({"tur": "adres", "okundu": True, "kaynak": "kod", "eposta_eslesti": True}, None),
        ({"tur": "adres", "okundu": False, "kaynak": "kod"}, None),  # açılmadı: tutarsızlık değil
    ],
)
def test_belge_tutarsizligi_kurali(capa, neden):
    from app.agents.dogrulama.capalar import belge_tutarsizliklari

    assert [b["neden"] for b in belge_tutarsizliklari([capa])] == ([neden] if neden else [])


def test_celiski_yalnizca_alintisi_metinde_olan():
    from app.agents.dogrulama.cekirdek import DegerlendirmeGirdisi, kalemi_degerlendir
    from app.agents.dogrulama.cikarim import IddiaDestegi, KanitCikarimi
    from app.agents.dogrulama.kurallar import OkunanKanit
    from app.core.kanit_okuma.belge import ErisimDurumu, KaynakSeviyesi

    okunan = OkunanKanit(
        erisim=ErisimDurumu.ACIK,
        seviye=KaynakSeviyesi.KAMUYA_ACIK,
        metin="Proje ekibi: takım lideri Ayşe Kaya, arayüz Elif.",
        url="https://ornek.com",
    )

    async def cikar(_alanlar):
        return KanitCikarimi(
            ilgili_mi=True,
            sonuc_var=False,
            sonuc_sayisal=False,
            sonuc_olcut_acik=False,
            pay_var=True,
            pay_ozgul=True,
            destekler=[
                IddiaDestegi(iddia="pay", durum="celisiyor", alinti="takım lideri Ayşe Kaya"),
                IddiaDestegi(iddia="is", durum="celisiyor", alinti="metinde olmayan cümle"),
            ],
        )

    girdi = DegerlendirmeGirdisi(baslik="Site", pay="Takımı ben yönettim")
    sonuc = asyncio.run(kalemi_degerlendir(girdi, [okunan], cikar))
    assert sonuc.parca_celiskileri == (({"iddia": "pay", "alinti": "takım lideri Ayşe Kaya"},),)
    assert sonuc.puanlar.rol == 1  # çelişki tavanı (puan kuralı değişmedi)


@pytest.fixture
def celisen_degerlendirme(monkeypatch):
    from app.agents.dogrulama.cikarim import IddiaDestegi, KanitCikarimi
    from app.servisler.dogrulama import kanit as kanit_servisi

    async def cikar(_alanlar):
        return KanitCikarimi(
            ilgili_mi=True,
            sonuc_var=True,
            sonuc_sayisal=True,
            sonuc_olcut_acik=True,
            pay_var=True,
            pay_ozgul=True,
            destekler=[IddiaDestegi(iddia="is", durum="celisiyor", alinti="Proje sayfası")],
        )

    monkeypatch.setattr(kanit_servisi, "cikar", cikar)


@pytest.mark.usefixtures("sahte_degerlendirme", "celisen_degerlendirme")
def test_celisen_kanit_kuyruga_bir_kez_duser():
    from app.models.inceleme_isareti import TUR_KANIT_CELISIYOR

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(oturum)
            yanit = await istemci.post(
                f"/dogrulama/kalem/{kalem_id}/kanit", headers=baslik, json={"url": LINK}
            )
            assert yanit.status_code == 201, yanit.text
            assert yanit.json()["guven_skoru"]["kanit_orijinalligi"] == 1  # tavan, işaretten değil
            [isaret] = await _isaretler(oturum, TUR_KANIT_CELISIYOR, [kalem_id])
            [celiski] = isaret.ayrinti["celiskiler"]
            assert (celiski["iddia"], celiski["alinti"], celiski["adres"]) == (
                "is",
                "Proje sayfası",
                LINK,
            )
            # İtiraz aynı çelişkiyi yeniden üretir: işarete ikinci kez eklenmez.
            yanit = await istemci.post(
                f"/dogrulama/kalem/{kalem_id}/itiraz",
                headers=baslik,
                json={"aciklama": "Sayfa benim projem"},
            )
            assert yanit.status_code == 200, yanit.text
            [isaret] = await _isaretler(oturum, TUR_KANIT_CELISIYOR, [kalem_id])
            assert len(isaret.ayrinti["celiskiler"]) == 1

    asyncio.run(senaryo())


@pytest.mark.usefixtures("sahte_degerlendirme", "dosya_modele_okutulmaz", "depo")
def test_bozuk_imzali_belge_isaret_acar(monkeypatch):
    from app.models.inceleme_isareti import TUR_BELGE_TUTARSIZ
    from app.servisler.dogrulama import dosyalar

    async def capalar(_girdi):
        return [{"tur": "imza", "gecerli": False, "butun": False, "imzalayan": "X"}]

    monkeypatch.setattr(dosyalar, "capalari_dogrula", capalar)

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(oturum)
            yanit = await istemci.post(
                f"/dogrulama/kalem/{kalem_id}/dosya",
                headers=baslik,
                files={"dosya": ("sertifika.pdf", _pdf())},
            )
            assert yanit.status_code == 201, yanit.text
            assert yanit.json()["guven_skoru"]["kanit_orijinalligi"] == 1  # D: çapasız gibi
            [isaret] = await _isaretler(oturum, TUR_BELGE_TUTARSIZ, [kalem_id])
            [bulgu] = isaret.ayrinti["bulgular"]
            assert (bulgu["neden"], bulgu["dosya_adi"]) == ("bozuk_imza", "sertifika.pdf")

    asyncio.run(senaryo())


# --- "Doğrulanamadı" etiketi ve karara itiraz -------------------------------------------------


def test_dogrulanamadi_etiketi_son_karara_gore():
    import datetime as dt
    from types import SimpleNamespace as N

    from app.agents.inceleme_durumu import gecerli_dogrulanamadilar

    def k(tur, durum, gun):
        return N(
            tur=tur,
            durum=durum,
            kapanma_tarihi=None if durum == "acik" else dt.datetime(2026, 10, gun, tzinfo=dt.UTC),
        )

    assert gecerli_dogrulanamadilar([]) == []
    assert [i.tur for i in gecerli_dogrulanamadilar([k("a", "dogrulanamadi", 1)])] == ["a"]
    # Açık işaret etiketi kaldırmaz; yeni "sorun yok" kararı kaldırır
    assert len(gecerli_dogrulanamadilar([k("a", "dogrulanamadi", 1), k("a", "acik", 2)])) == 1
    assert gecerli_dogrulanamadilar([k("a", "dogrulanamadi", 1), k("a", "kapandi", 2)]) == []
    assert len(gecerli_dogrulanamadilar([k("a", "kapandi", 1), k("b", "dogrulanamadi", 2)])) == 1


@pytest.mark.usefixtures("sahte_degerlendirme", "celisen_degerlendirme")
def test_dogrulanamadi_gorunur_itiraz_girvaka_gider_sorun_yok_etiketi_kaldirir():
    from app.models.inceleme_isareti import TUR_KANIT_CELISIYOR

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            baslik, _, kalem_id = await _genc_ve_kalem(oturum)
            yanit = await istemci.post(
                f"/dogrulama/kalem/{kalem_id}/kanit", headers=baslik, json={"url": LINK}
            )
            puan = yanit.json()["guven_skoru"]["kanit_orijinalligi"]
            assert yanit.json()["dogrulanamadi"] is False
            [isaret] = await _isaretler(oturum, TUR_KANIT_CELISIYOR, [kalem_id])

            isaret.durum = "dogrulanamadi"
            isaret.girvak_notu = "Kaynak başka birine ait görünüyor"
            isaret.kapanma_tarihi = dt.datetime.now(dt.UTC)
            await oturum.commit()
            durum = (await istemci.get(f"/dogrulama/kalem/{kalem_id}", headers=baslik)).json()
            assert durum["dogrulanamadi"] is True
            assert durum["girvak_notlari"] == ["Kaynak başka birine ait görünüyor"]
            assert durum["guven_skoru"]["kanit_orijinalligi"] == puan  # puan değişmedi (İ1)

            # İtiraz modeli çağırmaz, hak harcamaz; aynı türden yeni işaret GİRVAK'a gider
            yanit = await istemci.post(
                f"/dogrulama/kalem/{kalem_id}/itiraz",
                headers=baslik,
                json={"aciklama": "Proje benim, hesabı bağladım"},
            )
            assert yanit.status_code == 202, yanit.text
            assert yanit.json()["inceleme_bekliyor"] is True
            assert yanit.json()["dogrulanamadi"] is True  # karar sürüyor
            acik = [
                i
                for i in await _isaretler(oturum, TUR_KANIT_CELISIYOR, [kalem_id])
                if i.durum == "acik"
            ]
            assert [i.ayrinti["itiraz_notlari"] for i in acik] == [["Proje benim, hesabı bağladım"]]

            # GİRVAK itirazı "sorun yok" diye kapatınca etiket kalkar
            acik[0].durum = "kapandi"
            acik[0].kapanma_tarihi = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=5)
            await oturum.commit()
            durum = (await istemci.get(f"/dogrulama/kalem/{kalem_id}", headers=baslik)).json()
            assert durum["dogrulanamadi"] is False and durum["inceleme_bekliyor"] is False

    asyncio.run(senaryo())
