"""Genç–ilan uygunluk kararı (docs/matching-algorithm.md § 8, düşük riskli sürüm).

Firma–firma'nın mekanizması (yargı penceresi, gizli kayıtların saklanması, hata → bilinmiyor,
karar verilmiş kayda dokunmama) genç ilanında da çalışır; tek fark: genç tarafında rozet yok.
Gerçek model çağrısı yok, yargı çağrısı sahte.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.agents import eslestirme as ajan
from app.agents.eslestirme import BILINMIYOR, Yargi
from app.agents.uygunluk import KISMEN, UYGUN, UYGUN_DEGIL, gosterilecek_karar
from app.core.llm import HizSinirHatasi
from app.models.eslesme import Eslesme
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.yetenek_karti import YetenekKarti
from app.servisler import eslestirme as servis
from app.servisler.kart_duzenleme import kart_degisti
from tests.test_firma_eslestirme import V
from tests.test_sahiplik import _hesap, senaryo
from tests.test_uygunluk_karari import _cikti, _SahteZincir, _vektor

# --- Saf kurallar ve istem -------------------------------------------------------------


def test_genc_adayinda_karar_yanita_cikmaz():
    assert [gosterilecek_karar(k, firma_adayi=False) for k in (UYGUN, KISMEN, None)] == [None] * 3
    assert [gosterilecek_karar(k, firma_adayi=True) for k in (UYGUN, KISMEN, None)] == [
        UYGUN,
        KISMEN,
        None,
    ]


def test_genc_istemi_gerekce_talimati_ve_ayni_ek_kural():
    """Ölçümdeki genç istemiyle aynı (gerekçe talimatı + firma tarafının ek kuralı); sonda
    yalnızca karardan sonra yazılan aday metni kuralı (G9) var."""
    sistem = ajan.GENC_UYGUNLUK_SABLONU.messages[0].prompt.template
    assert sistem == ajan.GEREKCE_TALIMATI + ajan.UYGUNLUK_EK_KURALI + ajan.GENC_ADAY_KURALI
    insan = ajan.GENC_UYGUNLUK_SABLONU.messages[1].prompt.template
    assert "gerekçesini ve uygunluk kararını ver." in insan
    assert "YETENEK KARTI" in insan


def _genc_aday(guclu_kanit: bool):
    cikti = SimpleNamespace(
        guven_skoru=SimpleNamespace(
            kanit_orijinalligi=3 if guclu_kanit else 0, ucuncu_taraf_onayi=None
        )
    )
    kart = SimpleNamespace(id="k1", somut_ciktilar=[cikti])
    return SimpleNamespace(yetenek_karti=kart, tamamlanan_pilot=0, aday_kimligi="k1")


def test_genc_yargisinda_dogrulanmis_iddiasi_korumasi(monkeypatch):
    zincir = _SahteZincir(
        _cikti("Kartı doğrulanmış biri.", UYGUN), _cikti("İşi yapmış biri.", UYGUN)
    )
    monkeypatch.setattr(ajan, "_genc_uygunluk_zinciri", lambda: zincir)
    monkeypatch.setattr(
        ajan,
        "gerekce_girdileri",
        lambda ihtiyac, kart, ek_not="", tamamlanan_pilot=0: {"n": ek_not},
    )
    yargi = asyncio.run(ajan.genc_uygunluk_yargila(None, _genc_aday(guclu_kanit=False)))
    assert yargi == Yargi("İşi yapmış biri.", UYGUN)
    assert [g["n"] == ajan.DUZELTME_NOTU for g in zincir.girdiler] == [False, True]


def test_genc_yargisinda_iki_denemede_de_iddia_bilinmiyor(monkeypatch):
    zincir = _SahteZincir(_cikti("Doğrulandı.", UYGUN_DEGIL), _cikti("Kanıtlanmış.", UYGUN_DEGIL))
    monkeypatch.setattr(ajan, "_genc_uygunluk_zinciri", lambda: zincir)
    monkeypatch.setattr(ajan, "gerekce_girdileri", lambda *a, **k: {})
    assert asyncio.run(ajan.genc_uygunluk_yargila(None, _genc_aday(False))) == BILINMIYOR


# --- Pipeline --------------------------------------------------------------------------


class GencYargici:
    """Sahte yargı çağrısı: genç adına (rol_alani) göre karar; çağrıları sayar."""

    def __init__(self, kararlar: dict[str, object], varsayilan=UYGUN):
        self.kararlar, self.varsayilan = kararlar, varsayilan
        self.cagrilar: list[str] = []

    async def __call__(self, ihtiyac, aday):
        ad = aday.yetenek_karti.rol_alani
        self.cagrilar.append(ad)
        karar = self.kararlar.get(ad, self.varsayilan)
        if isinstance(karar, type) and issubclass(karar, Exception):
            raise karar("model hatası")
        return Yargi(f"{ad} gerekçesi.", karar)


@pytest.fixture
def yargici(monkeypatch):
    def kur(kararlar=None, varsayilan=UYGUN) -> GencYargici:
        y = GencYargici(kararlar or {}, varsayilan)
        monkeypatch.setattr(servis, "genc_uygunluk_yargila", y)
        return y

    return kur


async def _gencler(d, adet: int):
    """G0..G{adet-1}: ilana (V) sırayla biraz daha az benzer."""
    kisiler = []
    for k in range(adet):
        kisi = await _hesap(d.oturum, "genc", f"G{k}")
        kisi.kart = YetenekKarti(
            kullanici_id=kisi.profil.id,
            rol_alani=f"G{k}",
            deneyim_seviyesi="orta",
            embedding=_vektor(k),
            somut_ciktilar=[],
        )
        d.oturum.add(kisi.kart)
        kisiler.append(kisi)
    await d.oturum.flush()
    return kisiler


async def _genc_ilani(d) -> IhtiyacKarti:
    ilan = IhtiyacKarti(kurum_id=d.kurum1.profil.id, problem_tanimi="Genç ilanı", embedding=V)
    d.oturum.add(ilan)
    await d.oturum.commit()
    return ilan


async def _adlar(d) -> dict:
    return {k.id: k.rol_alani for k in await d.oturum.scalars(select(YetenekKarti))}


async def _kayitlar(d, ilan) -> dict[str, Eslesme]:
    """Gizliler dahil bütün kayıtlar, genç adına (rol_alani) göre."""
    satirlar = await d.oturum.scalars(
        select(Eslesme)
        .where(Eslesme.ihtiyac_karti_id == ilan.id)
        .execution_options(populate_existing=True)
    )
    adlar = await _adlar(d)
    return {adlar[e.yetenek_karti_id]: e for e in satirlar}


async def _listelenenler(d, ilan) -> list[str]:
    adlar = await _adlar(d)
    return [adlar[e.yetenek_karti_id] for e in await servis.pipeline_calistir(d.oturum, ilan)]


def test_genc_ilaninda_uygun_degil_gizlenir_ve_saklanir(yargici):
    async def adimlar(istemci, d):
        kisiler = await _gencler(d, 7)
        ilan = await _genc_ilani(d)
        y = yargici({"G1": UYGUN_DEGIL, "G3": UYGUN_DEGIL, "G2": KISMEN})

        assert sorted(await _listelenenler(d, ilan)) == ["G0", "G2", "G4", "G5", "G6"]
        assert sorted(y.cagrilar) == [f"G{k}" for k in range(7)]  # her aday bir kez
        kayit = await _kayitlar(d, ilan)
        assert len(kayit) == 7
        assert kayit["G1"].uygunluk == UYGUN_DEGIL and kayit["G2"].uygunluk == KISMEN

        # İkinci hesapta model çağrısı yok: gizli kayıtlar "hesaplanmış" demek.
        onceki = len(y.cagrilar)
        await servis.pipeline_calistir(d.oturum, ilan)
        assert len(y.cagrilar) == onceki

        # Gizli kaydın sahibi fırsatını görmez; kısmen olanın fırsatı durur.
        gizli = await istemci.get("/eslestirme/firsatlarim", headers=kisiler[1].baslik)
        assert gizli.status_code == 200 and gizli.json() == []
        kismen = await istemci.get("/eslestirme/firsatlarim", headers=kisiler[2].baslik)
        assert len(kismen.json()) == 1

    senaryo(adimlar)


def test_kurum_ekraninda_genc_icin_rozet_karari_donmez(yargici):
    """Kısmen (ve uygun) genç adayında yanıttaki karar null; gizli olan yine listede yok."""

    async def adimlar(istemci, d):
        await _gencler(d, 3)
        ilan = await _genc_ilani(d)
        yargici({"G1": KISMEN, "G2": UYGUN_DEGIL})

        yanit = await istemci.get(
            f"/eslestirme/oneriler/{d.kurum1.profil.id}",
            params={"ihtiyac_karti_id": str(ilan.id)},
            headers=d.kurum1.baslik,
        )
        assert yanit.status_code == 200
        oneriler = yanit.json()["oneriler"]
        assert [o["aday_turu"] for o in oneriler] == ["genc", "genc"]  # G2 gizli
        assert [o["uygunluk"] for o in oneriler] == [None, None]
        kayit = await _kayitlar(d, ilan)
        assert kayit["G1"].uygunluk == KISMEN  # saklanan karar durur, yalnızca yanıta çıkmaz

    senaryo(adimlar)


def test_genc_yargisi_hata_alirsa_bilinmiyor_listelenir_sonra_yeniden_denenir(yargici):
    async def adimlar(istemci, d):
        await _gencler(d, 2)
        ilan = await _genc_ilani(d)
        y = yargici({"G0": HizSinirHatasi})

        assert sorted(await _listelenenler(d, ilan)) == ["G0", "G1"]
        kayit = await _kayitlar(d, ilan)
        # Hata uygun_degil üretmez: karar da gerekçe de yok, öneri bugünkü gibi listelenir.
        assert (kayit["G0"].uygunluk, kayit["G0"].gerekce_metni) == (None, None)
        assert kayit["G1"].uygunluk == UYGUN
        assert y.cagrilar.count("G0") == 1  # aynı hesapta bir daha denenmedi

        # Sonraki hesapta yalnızca kararsız olan yeniden denenir.
        y.kararlar["G0"] = UYGUN_DEGIL
        assert await _listelenenler(d, ilan) == ["G1"]
        assert y.cagrilar == ["G0", "G1", "G0"]
        assert (await _kayitlar(d, ilan))["G0"].uygunluk == UYGUN_DEGIL

    senaryo(adimlar)


def test_karar_verilmis_genc_kaydi_yargilanmaz_ve_korunur(yargici):
    async def adimlar(istemci, d):
        await _gencler(d, 3)
        ilan = await _genc_ilani(d)
        y = yargici({})
        await servis.pipeline_calistir(d.oturum, ilan)

        kayit = await _kayitlar(d, ilan)
        kayit["G0"].durum, kayit["G0"].uygunluk, kayit["G0"].gerekce_metni = (
            "ilgileniliyor",
            None,
            "eski gerekçe",
        )
        kayit["G1"].durum, kayit["G1"].uygunluk = "genc_ilgilendi", KISMEN
        await d.oturum.commit()
        y.cagrilar.clear()
        y.varsayilan = UYGUN_DEGIL  # yargılansalardı elenirlerdi

        await servis.pipeline_calistir(d.oturum, ilan)
        assert y.cagrilar == []
        kayit = await _kayitlar(d, ilan)
        assert (kayit["G0"].durum, kayit["G0"].uygunluk, kayit["G0"].gerekce_metni) == (
            "ilgileniliyor",
            None,
            "eski gerekçe",
        )
        assert (kayit["G1"].durum, kayit["G1"].uygunluk) == ("genc_ilgilendi", KISMEN)

    senaryo(adimlar)


def test_genc_karti_duzenlenince_karar_gerekceyle_sifirlanir(yargici):
    async def adimlar(istemci, d):
        kisiler = await _gencler(d, 2)
        ilan = await _genc_ilani(d)
        y = yargici({"G0": UYGUN_DEGIL})
        await servis.pipeline_calistir(d.oturum, ilan)
        kayit = await _kayitlar(d, ilan)
        assert kayit["G0"].uygunluk == UYGUN_DEGIL

        await kart_degisti(d.oturum, kisiler[0].kart)
        await d.oturum.commit()
        kayit = await _kayitlar(d, ilan)
        # Gizli kayıt da sıfırlanır; karşıdaki kartın kaydına dokunulmaz.
        assert (kayit["G0"].uygunluk, kayit["G0"].gerekce_metni) == (None, None)
        assert kayit["G1"].uygunluk == UYGUN

        y.cagrilar.clear()
        y.kararlar["G0"] = KISMEN
        assert sorted(await _listelenenler(d, ilan)) == ["G0", "G1"]
        assert y.cagrilar == ["G0"]  # yalnızca düzenlenen kart yeniden yargılandı

    senaryo(adimlar)
