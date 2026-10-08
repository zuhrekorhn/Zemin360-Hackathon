"""Gençten ilgi: durum makinesi, uçlar ve korunan kayıt.

Belgeler: docs/kimlik-ve-dongu.md § 5, docs/kararlar.md G14.

Firmanın ilgisiyle başlayan akış aynen duruyor (tests/test_eslesme_durumu.py);
burada ikinci kapı: genç ilgi gösterir, kurum da ilgilenirse karşılıklı ilgi.
"""

import asyncio
import itertools
import math
import random
import uuid

import pytest
from sqlalchemy import func, select

from app.agents.eslesme_durumu import (
    GECISLER,
    IHTIYAC_KAPALI,
    OLAY_GENC_ILGI,
    OLAY_IHTIYAC_KAPANDI,
    OLAY_ILGILENIYORUM,
    OLAY_ILGIYI_GERI_CEK,
    OLAY_KABUL,
    OLAY_RED,
    OLAY_SIMDILIK_DEGIL,
    OLAYIN_ROLU,
    GecersizGecis,
    GecisSonucu,
    RolUygunDegil,
    gecis,
    ilgi_engeli,
)
from app.api.auth import hesap_olustur
from app.db.base import EMBEDDING_DIM
from app.models.bildirim import TUR_FIRSAT_KAPANDI, TUR_GENC_ILGI, Bildirim
from app.models.eslesme import Eslesme
from app.models.guven_skoru import GuvenSkoru
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.isbirligi import Isbirligi
from app.models.kullanici import Kullanici
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler import eslestirme as eslestirme_servisi
from app.servisler.ilgi import ihtiyaci_kapat
from tests.test_sahiplik import _hesap, durumlar, senaryo
from tests.veritabani import api_istemcisi, geri_alinan_oturum

# --- Durum tablosu (saf) --------------------------------------------------------------------

DURUMLAR = (
    "onerildi",
    "genc_ilgilendi",
    "ilgileniliyor",
    "kabul_edildi",
    "reddedildi",
    "kapandi",
)
OLAYLAR = (
    OLAY_ILGILENIYORUM,
    OLAY_KABUL,
    OLAY_RED,
    OLAY_GENC_ILGI,
    OLAY_ILGIYI_GERI_CEK,
    OLAY_SIMDILIK_DEGIL,
    OLAY_IHTIYAC_KAPANDI,
)
ROLLER = ("genc", "kurum", "girvak", "sistem")

# Plan § 4.2'nin tablosu, birebir: (durum, olay) → yeni durum.
GECERLI = {
    ("onerildi", OLAY_ILGILENIYORUM): "ilgileniliyor",
    ("ilgileniliyor", OLAY_KABUL): "kabul_edildi",
    ("ilgileniliyor", OLAY_RED): "reddedildi",
    ("onerildi", OLAY_GENC_ILGI): "genc_ilgilendi",
    ("genc_ilgilendi", OLAY_ILGIYI_GERI_CEK): "onerildi",
    ("genc_ilgilendi", OLAY_ILGILENIYORUM): "kabul_edildi",
    ("genc_ilgilendi", OLAY_SIMDILIK_DEGIL): "kapandi",
    ("onerildi", OLAY_IHTIYAC_KAPANDI): "kapandi",
    ("genc_ilgilendi", OLAY_IHTIYAC_KAPANDI): "kapandi",
    ("ilgileniliyor", OLAY_IHTIYAC_KAPANDI): "kapandi",
}
# Aynı geçişin tekrarı (200, yan etkisiz). `kabul_edildi` + ilgileniyorum yalnızca
# karşılıklı ilgide (genç başlattı) tekrar; kurum başlattıysa 409.
TEKRAR = {
    ("ilgileniliyor", OLAY_ILGILENIYORUM),
    ("kabul_edildi", OLAY_KABUL),
    ("reddedildi", OLAY_RED),
    ("genc_ilgilendi", OLAY_GENC_ILGI),
    ("onerildi", OLAY_ILGIYI_GERI_CEK),
    ("kapandi", OLAY_SIMDILIK_DEGIL),
    ("kapandi", OLAY_IHTIYAC_KAPANDI),
}


def test_tablo_plandakiyle_ayni():
    assert {(kaynak, olay): hedef for (olay, kaynak), (_, hedef) in GECISLER.items()} == GECERLI


@pytest.mark.parametrize(
    "durum,olay,rol,baslatan",
    list(itertools.product(DURUMLAR, OLAYLAR, ROLLER, (None, "genc", "kurum"))),
)
def test_her_uclu(durum, olay, rol, baslatan):
    if rol != OLAYIN_ROLU[olay]:
        with pytest.raises(RolUygunDegil):
            gecis(durum, olay, rol, baslatan=baslatan)
        return
    if (durum, olay) in GECERLI:
        assert gecis(durum, olay, rol, baslatan=baslatan) == GecisSonucu(
            GECERLI[(durum, olay)], degisti=True
        )
        return
    tekrar = (durum, olay) in TEKRAR or (
        (durum, olay) == ("kabul_edildi", OLAY_ILGILENIYORUM) and baslatan == "genc"
    )
    if tekrar:
        assert gecis(durum, olay, rol, baslatan=baslatan) == GecisSonucu(durum, degisti=False)
    else:
        with pytest.raises(GecersizGecis) as hata:
            gecis(durum, olay, rol, baslatan=baslatan)
        assert "şu an" in str(hata.value)


def test_karsilikli_ilgiden_sonra_geri_cekilemez():
    with pytest.raises(GecersizGecis):
        gecis("kabul_edildi", OLAY_ILGIYI_GERI_CEK, "genc", baslatan="genc")


@pytest.mark.parametrize(
    "ihtiyac_durumu,engel",
    [
        ("acik", None),
        ("kapandi", IHTIYAC_KAPALI),
    ],
)
def test_ilgi_engeli(ihtiyac_durumu, engel):
    """Skor eşiği kalktı (giriş kararı benzerlik tabanında); engel yalnızca kapalı ihtiyaç."""
    assert ilgi_engeli(ihtiyac_durumu) == engel


# --- Uçlar (gerçek veritabanı; dünya tests/test_sahiplik.py) --------------------------------

ONAY = {"iletisim_onayi": True}


async def _eslesme(d, eslesme_id):
    return await d.oturum.scalar(
        select(Eslesme).where(Eslesme.id == eslesme_id).execution_options(populate_existing=True)
    )


def test_karsilikli_ilgi_iletisimi_ve_is_birligini_acar(plan_arka_plan_isi_yok):
    async def adimlar(istemci, d):
        e1 = str(d.E1.id)
        yol = f"/eslestirme/{e1}"
        epostalar = {d.genc1.hesap.email, d.kurum1.hesap.email}

        assert (
            await istemci.post(f"{yol}/genc-ilgi", headers=d.genc1.baslik, json={})
        ).status_code == 422  # iletişim onayı zorunlu
        ilgi = await istemci.post(f"{yol}/genc-ilgi", headers=d.genc1.baslik, json=ONAY)
        assert ilgi.status_code == 200
        assert ilgi.json()["durum"] == "genc_ilgilendi"
        assert ilgi.json()["iletisim"] is None
        tekrar = await istemci.post(f"{yol}/genc-ilgi", headers=d.genc1.baslik, json=ONAY)
        assert tekrar.status_code == 200

        # Firma ilgiyi görür; e-posta hâlâ hiçbir yanıtta yok.
        oneriler = await istemci.get(
            f"/eslestirme/oneriler/{d.kurum1.profil.id}", headers=d.kurum1.baslik
        )
        satir = next(o for o in oneriler.json()["oneriler"] if o["eslesme_id"] == e1)
        assert satir["genc_ilgi_gosterdi"] is True
        assert satir["skor"] == pytest.approx(0.6)  # ilgi skoru değiştirmez
        assert not any(e in oneriler.text for e in epostalar)
        bildirim = await d.oturum.scalar(
            select(Bildirim).where(
                Bildirim.hesap_id == d.kurum1.hesap.id, Bildirim.tur == TUR_GENC_ILGI
            )
        )
        assert "Elif" in bildirim.metin and "@" not in bildirim.metin

        # Firma da ilgilenir: karşılıklı ilgi, genç ayrıca onay vermez.
        karsilik = await istemci.post(
            "/eslestirme/ilgileniyorum", headers=d.kurum1.baslik, json={"eslesme_id": e1}
        )
        assert karsilik.status_code == 200
        assert karsilik.json()["durum"] == "kabul_edildi"
        # `aday_firma_email` genç eşleşmesinde boş (docs/kararlar.md F11).
        assert set(karsilik.json()["iletisim"].values()) - {None} == epostalar
        assert karsilik.json()["isbirligi_id"] is not None
        assert plan_arka_plan_isi_yok == [uuid.UUID(karsilik.json()["isbirligi_id"])]
        # Çift tıklama: 200, ikinci iş birliği ve ikinci plan yok.
        ikinci = await istemci.post(
            "/eslestirme/ilgileniyorum", headers=d.kurum1.baslik, json={"eslesme_id": e1}
        )
        assert ikinci.status_code == 200
        assert (
            await d.oturum.scalar(
                select(func.count()).select_from(Isbirligi).where(Isbirligi.eslesme_id == d.E1.id)
            )
            == 1
        )
        assert len(plan_arka_plan_isi_yok) == 1
        # Karşılıklıdan sonra geri çekilemez.
        assert (
            await istemci.post(f"{yol}/ilgiyi-geri-cek", headers=d.genc1.baslik)
        ).status_code == 409

    senaryo(adimlar)


def test_geri_cekme_ve_simdilik_degil():
    async def adimlar(istemci, d):
        yol = f"/eslestirme/{d.E1.id}"
        await istemci.post(f"{yol}/genc-ilgi", headers=d.genc1.baslik, json=ONAY)
        geri = await istemci.post(f"{yol}/ilgiyi-geri-cek", headers=d.genc1.baslik)
        assert geri.json()["durum"] == "onerildi"
        eslesme = await _eslesme(d, d.E1.id)
        assert (eslesme.baslatan, eslesme.genc_iletisim_onayi_tarihi) == (None, None)

        await istemci.post(f"{yol}/genc-ilgi", headers=d.genc1.baslik, json=ONAY)
        kapat = await istemci.post(f"{yol}/simdilik-degil", headers=d.kurum1.baslik)
        assert kapat.json()["durum"] == "kapandi"
        bildirim = await d.oturum.scalar(
            select(Bildirim).where(
                Bildirim.hesap_id == d.genc1.hesap.id, Bildirim.tur == TUR_FIRSAT_KAPANDI
            )
        )
        assert bildirim.metin == "Koop Bir tarafındaki fırsat kapandı."
        # Kapandıktan sonra yeniden ilgi gösterilemez.
        assert (
            await istemci.post(f"{yol}/genc-ilgi", headers=d.genc1.baslik, json=ONAY)
        ).status_code == 409

    senaryo(adimlar)


def test_ilgi_ac_kapa_firmaya_tek_bildirim_yazar():
    """İlgi göster, geri çek, yeniden göster: geçişler uygulanır ama firma 24 saatte
    aynı eşleşme için tek bildirim alır."""

    async def adimlar(istemci, d):
        yol = f"/eslestirme/{d.E1.id}"
        for _ in range(3):
            assert (
                await istemci.post(f"{yol}/genc-ilgi", headers=d.genc1.baslik, json=ONAY)
            ).json()["durum"] == "genc_ilgilendi"
            assert (await istemci.post(f"{yol}/ilgiyi-geri-cek", headers=d.genc1.baslik)).json()[
                "durum"
            ] == "onerildi"
        sayi = await d.oturum.scalar(
            select(func.count())
            .select_from(Bildirim)
            .where(Bildirim.hesap_id == d.kurum1.hesap.id, Bildirim.tur == TUR_GENC_ILGI)
        )
        assert sayi == 1

    senaryo(adimlar)


def test_kapali_ihtiyaca_ilgi_gosterilemez_skor_engellemez():
    """Eskiden skor eşiğinin altı 409'du; eşik kalktı, düşük skor ilgiyi engellemez."""

    async def adimlar(istemci, d):
        yol = f"/eslestirme/{d.E1.id}/genc-ilgi"
        d.E1.skor = 0.2
        d.I1.durum = "kapandi"
        await d.oturum.commit()
        kapali = await istemci.post(yol, headers=d.genc1.baslik, json=ONAY)
        assert (kapali.status_code, kapali.json()["detail"]) == (409, IHTIYAC_KAPALI)

    senaryo(adimlar)


def test_ilgi_uclarinin_yetkisi():
    async def adimlar(istemci, d):
        e1 = d.E1.id
        await durumlar(
            istemci,
            "POST",
            f"/eslestirme/{e1}/genc-ilgi",
            {None: 401, d.kurum1: 403, d.genc2: 404},
            json=ONAY,
        )
        await durumlar(
            istemci,
            "POST",
            f"/eslestirme/{e1}/ilgiyi-geri-cek",
            {None: 401, d.kurum1: 403, d.genc2: 404},
        )
        await durumlar(
            istemci,
            "POST",
            f"/eslestirme/{e1}/simdilik-degil",
            {None: 401, d.genc1: 403, d.kurum2: 404},
        )

    senaryo(adimlar)


def test_ihtiyac_kapaninca_bekleyenler_kapanir_kararlar_kalir():
    async def adimlar(istemci, d):
        # I1'de: E1 genç ilgi gösterdi; ayrıca kabul edilmiş ve önerilmiş kayıtlar.
        await istemci.post(f"/eslestirme/{d.E1.id}/genc-ilgi", headers=d.genc1.baslik, json=ONAY)
        kabul = Eslesme(
            ihtiyac_karti_id=d.I1.id, yetenek_karti_id=d.K2.id, skor=0.7, durum="kabul_edildi"
        )
        d.oturum.add(kabul)
        await d.oturum.commit()

        ihtiyac = await d.oturum.get(IhtiyacKarti, d.I1.id)
        assert await ihtiyaci_kapat(d.oturum, ihtiyac) == 1
        await d.oturum.commit()

        assert (await _eslesme(d, d.E1.id)).durum == "kapandi"
        assert (await _eslesme(d, kabul.id)).durum == "kabul_edildi"
        assert ihtiyac.durum == "kapandi"
        bildirimler = await d.oturum.scalar(
            select(func.count())
            .select_from(Bildirim)
            .where(Bildirim.hesap_id == d.genc1.hesap.id, Bildirim.tur == TUR_FIRSAT_KAPANDI)
        )
        assert bildirimler == 1

    senaryo(adimlar)


# --- G14: ilgi gösterilmiş kayıt korunur (gerçek pipeline) -------------------------------


def _yon() -> list[float]:
    vektor = [random.gauss(0, 1) for _ in range(EMBEDDING_DIM)]
    boy = math.sqrt(sum(x * x for x in vektor))
    return [x / boy for x in vektor]


@pytest.fixture
def gerekce_sahte(monkeypatch):
    async def gerekce(_ihtiyac, aday):
        return f"yeni gerekçe {aday.yetenek_karti.id}"

    monkeypatch.setattr(eslestirme_servisi, "gerekce_uret", gerekce)


async def _genc_karti(oturum, yon, *, dogrulanmis: bool) -> YetenekKarti:
    hesap = await hesap_olustur(
        oturum,
        email=f"test-{uuid.uuid4().hex[:10]}@ornek.com",
        sifre="yeterince-uzun",
        rol="genc",
        ad="Genç",
    )
    kullanici = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
    ciktilar = []
    if dogrulanmis:
        ciktilar = [
            SomutCikti(
                baslik="İş",
                guven_skoru=GuvenSkoru(
                    kanit_orijinalligi=3,
                    sonuc_olculebilirligi=3,
                    rol_netligi=3,
                    ucuncu_taraf_onayi=3,
                    gerekce_metni="g",
                ),
            )
        ]
    kart = YetenekKarti(
        kullanici_id=kullanici.id,
        rol_alani="r",
        deneyim_seviyesi="orta",
        embedding=yon,
        somut_ciktilar=ciktilar,
    )
    oturum.add(kart)
    await oturum.flush()
    return kart


def test_ilgi_gosterilmis_kayit_yeniden_hesapta_korunur(gerekce_sahte):
    """(a) Daha güçlü 5 kart gelip ilk 5'i doldurunca ilgili kayıt silinmez, skoru ve
    gerekçesi değişmez, firma yanıtında görünür. (c) Önerilmiş zayıf kayıt ise eskisi
    gibi silinir."""

    async def senaryo_():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            kurum = await _hesap(oturum, "kurum", "Koop")
            yon = _yon()
            ihtiyac = IhtiyacKarti(kurum_id=kurum.profil.id, problem_tanimi="p", embedding=yon)
            oturum.add(ihtiyac)
            ilgili = await _genc_karti(oturum, yon, dogrulanmis=False)
            onerilen = await _genc_karti(oturum, yon, dogrulanmis=False)
            await oturum.commit()
            await eslestirme_servisi.pipeline_calistir(oturum, ihtiyac)

            kayit = await oturum.scalar(
                select(Eslesme).where(Eslesme.yetenek_karti_id == ilgili.id)
            )
            kayit.durum, kayit.baslatan = "genc_ilgilendi", "genc"
            eski_skor, eski_gerekce = kayit.skor, kayit.gerekce_metni
            await oturum.commit()

            # Daha güçlü (doğrulanmış) beş kart gelir ve yeniden hesaplanır.
            for _ in range(5):
                await _genc_karti(oturum, yon, dogrulanmis=True)
            await oturum.commit()
            eslesmeler = await eslestirme_servisi.pipeline_calistir(oturum, ihtiyac)

            idler = {e.yetenek_karti_id: e for e in eslesmeler}
            assert ilgili.id in idler  # (a) silinmedi
            korunan = idler[ilgili.id]
            assert (korunan.durum, korunan.skor, korunan.gerekce_metni) == (
                "genc_ilgilendi",
                eski_skor,
                eski_gerekce,
            )
            assert onerilen.id not in idler  # (c) ilk 5'in dışına düşen öneri silindi
            assert sum(e.durum == "onerildi" for e in eslesmeler) == 5

            yanit = await istemci.get(
                f"/eslestirme/oneriler/{kurum.profil.id}?ihtiyac_karti_id={ihtiyac.id}",
                headers=kurum.baslik,
            )
            ilgi_gosterenler = [o for o in yanit.json()["oneriler"] if o["genc_ilgi_gosterdi"]]
            assert [o["yetenek_karti"]["id"] for o in ilgi_gosterenler] == [str(ilgili.id)]

    asyncio.run(senaryo_())


def test_ilgi_gosterilmis_kayit_kart_duzenlense_de_kalir(gerekce_sahte):
    """(b) Genç kartını ihtiyaca uymayacak biçimde değiştirir; kayıt ve skoru durur."""

    async def senaryo_():
        async with geri_alinan_oturum() as oturum:
            kurum = await _hesap(oturum, "kurum", "Koop")
            yon = _yon()
            ihtiyac = IhtiyacKarti(kurum_id=kurum.profil.id, problem_tanimi="p", embedding=yon)
            oturum.add(ihtiyac)
            kart = await _genc_karti(oturum, yon, dogrulanmis=False)
            await oturum.commit()
            await eslestirme_servisi.pipeline_calistir(oturum, ihtiyac)
            kayit = await oturum.scalar(select(Eslesme).where(Eslesme.yetenek_karti_id == kart.id))
            kayit.durum, kayit.baslatan = "genc_ilgilendi", "genc"
            eski_skor = kayit.skor
            await oturum.commit()

            # Kart artık tamamen başka bir şeyi anlatıyor (ters yön: benzerlik -1).
            kart.embedding = [-x for x in yon]
            await oturum.commit()
            eslesmeler = await eslestirme_servisi.pipeline_calistir(oturum, ihtiyac)

            korunan = [e for e in eslesmeler if e.yetenek_karti_id == kart.id]
            assert [(e.durum, e.skor) for e in korunan] == [("genc_ilgilendi", eski_skor)]

    asyncio.run(senaryo_())
