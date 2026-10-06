"""Firma–firma uygunluk kararı (docs/matching-algorithm.md § 8).

Benzerlik aday bulur, yapay zekâ doğrular, puanı kod verir. Gerçek model çağrısı yok:
yargı çağrısı sahte; kurallar ve pipeline'ın davranışı sınanır.

- saf kurallar: etiket doğrulama, görünürlük, listelenecekler
- pipeline: ilk 8'i yargıla / ilk 5'i listele, elenenin yerine sıradaki, saklama,
  tekrar hesapta model çağrısı yok, hata → bilinmiyor, karar verilmiş kayıt korunur
- `uygun_degil` hiçbir okuma ucunda görünmez (her uç için)
"""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.agents import eslestirme as ajan
from app.agents.eslestirme import BILINMIYOR, Yargi
from app.agents.uygunluk import (
    KISMEN,
    UYGUN,
    UYGUN_DEGIL,
    YARGI_N,
    gorunur_kosulu,
    gorunur_mu,
    karari_dogrula,
    listelenecekler,
)
from app.api.sahiplik import TARAF_ADAY, TARAF_ILAN
from app.core.llm import HizSinirHatasi
from app.db.base import EMBEDDING_DIM
from app.models.bildirim import TUR_YENI_ONERI, Bildirim
from app.models.eslesme import Eslesme
from app.models.ihtiyac_karti import IhtiyacKarti
from app.servisler import eslestirme as servis
from app.servisler import firma_karti as firma_servisi
from app.servisler.eslestirme import iliskileriyle
from tests.test_firma_eslestirme import _firma, _ortak_ilan
from tests.test_firma_eslestirme import gerekce_sahte as gerekce_sahte  # noqa: F401
from tests.test_sahiplik import senaryo

# --- Saf kurallar ----------------------------------------------------------------------


def test_etiket_dogrulama_gecersizi_bilinmiyor_yapar():
    assert [karari_dogrula(e) for e in (UYGUN, KISMEN, UYGUN_DEGIL)] == [UYGUN, KISMEN, UYGUN_DEGIL]
    # Geçersiz etiket asla uygun_degil'e çevrilmez: bilinmiyor (None).
    assert [karari_dogrula(e) for e in (None, "", "belki", "UYGUN", "uygun degil")] == [None] * 5


def test_yalnizca_uygun_degil_gizlenir():
    assert [gorunur_mu(k) for k in (UYGUN, KISMEN, None)] == [True, True, True]
    assert gorunur_mu(UYGUN_DEGIL) is False


def test_listelenecekler_elenenleri_atlar_bilinmeyeni_listeler():
    a, b, c, d, e, f = (uuid.uuid4() for _ in range(6))
    pencere = [a, b, c, d, e, f]
    kararlar = {a: UYGUN, b: UYGUN_DEGIL, c: KISMEN, d: None, e: UYGUN_DEGIL}
    # b ve e elenir; kararı olmayan f ile kararı None olan d listelenir.
    assert listelenecekler(pencere, kararlar, 5) == [a, c, d, f]
    assert listelenecekler(pencere, kararlar, 2) == [a, c]
    assert listelenecekler([], {}, 5) == []


def test_yargi_penceresi_listeden_buyuk():
    assert YARGI_N == 8 > ajan.TOP_N == 5


# --- Model çıktısı ---------------------------------------------------------------------


class _SahteZincir:
    def __init__(self, *cevaplar):
        self.cevaplar = list(cevaplar)
        self.girdiler: list[dict] = []

    async def ainvoke(self, girdi):
        self.girdiler.append(girdi)
        cevap = self.cevaplar.pop(0)
        if isinstance(cevap, Exception):
            raise cevap
        return cevap


def _cikti(gerekce, uygunluk):
    return SimpleNamespace(gerekce=gerekce, uygunluk=uygunluk)


@pytest.mark.parametrize(
    "cikti",
    [_cikti("Gerekçe.", "belki"), _cikti("Gerekçe.", None), _cikti("  ", "uygun"), None],
    ids=["gecersiz_etiket", "bos_etiket", "bos_gerekce", "cikti_yok"],
)
def test_gecersiz_cikti_bilinmiyor_sayilir(monkeypatch, cikti):
    monkeypatch.setattr(ajan, "_firma_uygunluk_zinciri", lambda: _SahteZincir(cikti))
    assert asyncio.run(ajan._firma_uygunluk_cagir({})) == BILINMIYOR


def test_gecerli_cikti_kirpilarak_doner(monkeypatch):
    monkeypatch.setattr(
        ajan, "_firma_uygunluk_zinciri", lambda: _SahteZincir(_cikti("  Yazılım yapıyor. ", KISMEN))
    )
    assert asyncio.run(ajan._firma_uygunluk_cagir({})) == Yargi("Yazılım yapıyor.", KISMEN)


def _aday(dogrulandi: bool):
    kurum = SimpleNamespace(dogrulama_durumu="dogrulandi" if dogrulandi else "dogrulanmadi")
    return SimpleNamespace(firma_karti=SimpleNamespace(kurum=kurum))


def test_dogrulanmis_iddiasi_korumasi_gerekceye_aynen_uygulanir(monkeypatch):
    """Doğrulanmamış firma "doğrulanmış" diye anlatılırsa düzeltme notuyla bir kez yeniden."""
    zincir = _SahteZincir(
        _cikti("Firma doğrulanmış ve işi yapıyor.", UYGUN), _cikti("İşi yapıyor.", UYGUN)
    )
    monkeypatch.setattr(ajan, "_firma_uygunluk_zinciri", lambda: zincir)
    monkeypatch.setattr(
        ajan, "firma_gerekce_girdileri", lambda ihtiyac, aday, ek_not="": {"ek_not": ek_not}
    )
    yargi = asyncio.run(ajan.firma_uygunluk_yargila(None, _aday(dogrulandi=False)))
    assert yargi == Yargi("İşi yapıyor.", UYGUN)
    assert [g["ek_not"] == ajan.FIRMA_DUZELTME_NOTU for g in zincir.girdiler] == [False, True]


def test_iki_denemede_de_iddia_varsa_gerekce_de_karar_da_bilinmiyor(monkeypatch):
    # Hatalı metne dayanan karara (uygun_degil dahil) güvenilmez.
    zincir = _SahteZincir(
        _cikti("Firma doğrulandı.", UYGUN_DEGIL), _cikti("Kanıtlanmış bir ortak.", UYGUN_DEGIL)
    )
    monkeypatch.setattr(ajan, "_firma_uygunluk_zinciri", lambda: zincir)
    monkeypatch.setattr(ajan, "firma_gerekce_girdileri", lambda *a, **k: {})
    assert asyncio.run(ajan.firma_uygunluk_yargila(None, _aday(dogrulandi=False))) == BILINMIYOR


def test_dogrulanmis_firmaya_koruma_uygulanmaz(monkeypatch):
    zincir = _SahteZincir(_cikti("Firma doğrulandı.", UYGUN))
    monkeypatch.setattr(ajan, "_firma_uygunluk_zinciri", lambda: zincir)
    monkeypatch.setattr(ajan, "firma_gerekce_girdileri", lambda *a, **k: {})
    yargi = asyncio.run(ajan.firma_uygunluk_yargila(None, _aday(dogrulandi=True)))
    assert yargi.uygunluk == UYGUN and len(zincir.girdiler) == 1


# --- Pipeline --------------------------------------------------------------------------


def _vektor(k: int) -> list[float]:
    """İlan vektörüne (V) k arttıkça biraz daha az benzeyen vektör: sıra F0, F1, F2, …"""
    return [1.0, 0.1 * k] + [0.0] * (EMBEDDING_DIM - 2)


class Yargici:
    """Sahte yargı çağrısı: firma adına göre karar; çağrıları sayar."""

    def __init__(self, kararlar: dict[str, object | None], varsayilan=UYGUN):
        self.kararlar, self.varsayilan = kararlar, varsayilan
        self.cagrilar: list[str] = []

    async def __call__(self, ihtiyac, aday):
        ad = aday.firma_karti.kurum.ad
        self.cagrilar.append(ad)
        karar = self.kararlar.get(ad, self.varsayilan)
        if isinstance(karar, Exception) or (
            isinstance(karar, type) and issubclass(karar, Exception)
        ):
            raise karar if isinstance(karar, Exception) else karar("model hatası")
        return Yargi(f"{ad} gerekçesi.", karar)


@pytest.fixture
def yargici(monkeypatch):
    """`yargici.kur(...)` sahte yargıcı bağlar (autouse sahtenin üstüne biner)."""

    def kur(kararlar=None, varsayilan=UYGUN) -> Yargici:
        y = Yargici(kararlar or {}, varsayilan)
        monkeypatch.setattr(servis, "firma_uygunluk_yargila", y)
        return y

    return SimpleNamespace(kur=kur)


async def _firmalar(d, adet: int):
    return [await _firma(d, f"F{k}", vektor=_vektor(k)) for k in range(adet)]


async def _kayitlar(d, ilan) -> dict[str, Eslesme]:
    """Gizliler dahil bütün kayıtlar, firma adına göre."""
    satirlar = await d.oturum.scalars(
        iliskileriyle(select(Eslesme))
        .where(Eslesme.ihtiyac_karti_id == ilan.id)
        .execution_options(populate_existing=True)
    )
    return {e.firma_karti.kurum.ad: e for e in satirlar}


async def _listelenenler(d, ilan) -> list[str]:
    eslesmeler = await servis.pipeline_calistir(d.oturum, ilan)
    return [e.firma_karti.kurum.ad for e in eslesmeler]


def test_uygun_degil_saklanir_listelenmez_ve_ilk_bes_dolar(yargici):
    async def adimlar(istemci, d):
        await _firmalar(d, 7)
        ilan = await _ortak_ilan(d)
        y = yargici.kur({"F1": UYGUN_DEGIL, "F3": UYGUN_DEGIL, "F2": KISMEN})

        assert sorted(await _listelenenler(d, ilan)) == ["F0", "F2", "F4", "F5", "F6"]
        # Her aday bir kez yargılandı: ilk dalga F0-F4, elenen ikisi yerine F5 ve F6.
        assert sorted(y.cagrilar) == [f"F{k}" for k in range(7)]
        kayit = await _kayitlar(d, ilan)
        assert len(kayit) == 7
        assert {ad: e.uygunluk for ad, e in kayit.items()} == {
            "F0": UYGUN,
            "F1": UYGUN_DEGIL,
            "F2": KISMEN,
            "F3": UYGUN_DEGIL,
            "F4": UYGUN,
            "F5": UYGUN,
            "F6": UYGUN,
        }
        assert kayit["F2"].gerekce_metni == "F2 gerekçesi."

    senaryo(adimlar)


def test_yargi_penceresi_sekizle_sinirli(yargici):
    async def adimlar(istemci, d):
        await _firmalar(d, 11)
        ilan = await _ortak_ilan(d)
        # İlk beşin hepsi elenir: listede yalnızca pencerenin kalanı (F5, F6, F7) olur.
        y = yargici.kur({f"F{k}": UYGUN_DEGIL for k in range(5)})
        assert sorted(await _listelenenler(d, ilan)) == ["F5", "F6", "F7"]
        assert sorted(y.cagrilar) == [f"F{k}" for k in range(8)]  # F8-F10 hiç yargılanmadı
        assert len(await _kayitlar(d, ilan)) == 8

    senaryo(adimlar)


def test_tekrar_hesapta_model_cagrisi_yok(yargici):
    async def adimlar(istemci, d):
        await _firmalar(d, 6)
        ilan = await _ortak_ilan(d)
        y = yargici.kur({"F1": UYGUN_DEGIL, "F4": KISMEN})
        ilk = await _listelenenler(d, ilan)
        cagri_sayisi = len(y.cagrilar)
        assert cagri_sayisi == 6

        # Gizli kayıt saklandığı için ikinci ve üçüncü hesap model çağırmaz, liste aynı.
        assert await _listelenenler(d, ilan) == ilk
        assert await _listelenenler(d, ilan) == ilk
        assert len(y.cagrilar) == cagri_sayisi

    senaryo(adimlar)


def test_hata_bilinmiyor_sayilir_listelenir_sonra_yeniden_denenir(yargici):
    async def adimlar(istemci, d):
        await _firmalar(d, 4)
        ilan = await _ortak_ilan(d)
        # Hız sınırı, zaman aşımı ve beklenmeyen hata: hiçbiri uygun_degil üretmez.
        y = yargici.kur({"F0": HizSinirHatasi, "F1": TimeoutError, "F2": ValueError})
        assert sorted(await _listelenenler(d, ilan)) == ["F0", "F1", "F2", "F3"]
        kayit = await _kayitlar(d, ilan)
        for ad in ("F0", "F1", "F2"):
            assert (kayit[ad].uygunluk, kayit[ad].gerekce_metni) == (None, None)
        assert kayit["F3"].uygunluk == UYGUN
        assert len(y.cagrilar) == 4  # aynı hesapta tekrar denenmedi

        # Sonraki hesapta yalnızca kararsız olanlar yeniden denenir.
        y2 = yargici.kur({"F1": UYGUN_DEGIL})
        assert sorted(await _listelenenler(d, ilan)) == ["F0", "F2", "F3"]
        assert sorted(y2.cagrilar) == ["F0", "F1", "F2"]
        kayit = await _kayitlar(d, ilan)
        assert kayit["F0"].uygunluk == UYGUN and kayit["F0"].gerekce_metni == "F0 gerekçesi."
        assert kayit["F1"].uygunluk == UYGUN_DEGIL

    senaryo(adimlar)


def test_gecersiz_etiket_donen_yargi_hicbir_zaman_uygun_degil_olmaz(yargici):
    async def adimlar(istemci, d):
        await _firmalar(d, 2)
        ilan = await _ortak_ilan(d)
        yargici.kur(varsayilan=None)  # her aday "bilinmiyor" döner
        assert sorted(await _listelenenler(d, ilan)) == ["F0", "F1"]
        assert all(e.uygunluk is None for e in (await _kayitlar(d, ilan)).values())

    senaryo(adimlar)


def test_karar_verilmis_kayit_yargilanmaz_ve_korunur(yargici):
    async def adimlar(istemci, d):
        await _firmalar(d, 4)
        ilan = await _ortak_ilan(d)
        yargici.kur()
        await _listelenenler(d, ilan)
        kayit = await _kayitlar(d, ilan)
        # F0: firma ilgilendi, F1: aday ilgilendi, F2: kabul. Hepsi kararsız ve gerekçesiz.
        for ad, durum in (
            ("F0", "ilgileniliyor"),
            ("F1", "genc_ilgilendi"),
            ("F2", "kabul_edildi"),
        ):
            kayit[ad].durum, kayit[ad].uygunluk, kayit[ad].gerekce_metni = durum, None, None
        kayit["F1"].gerekce_metni, kayit["F1"].skor = "ilgi gösterirken görülen gerekçe", 0.99
        kayit["F3"].uygunluk = None  # kararsız `onerildi`: tek yeniden yargılanacak kayıt
        await d.oturum.commit()

        y = yargici.kur(varsayilan=UYGUN_DEGIL)  # yargılansalar hepsi elenirdi
        await _listelenenler(d, ilan)
        # Yalnızca kararsız `onerildi` kayıt (F3) yeniden yargılandı; karar verilmişler hiç.
        assert y.cagrilar == ["F3"]
        kayit = await _kayitlar(d, ilan)
        assert [kayit[ad].durum for ad in ("F0", "F1", "F2")] == [
            "ilgileniliyor",
            "genc_ilgilendi",
            "kabul_edildi",
        ]
        assert [kayit[ad].uygunluk for ad in ("F0", "F1", "F2")] == [None, None, None]
        # İlgi gösterilmiş kaydın skoru ve gerekçesi değişmez (karar 14).
        assert (kayit["F1"].skor, kayit["F1"].gerekce_metni) == (
            0.99,
            "ilgi gösterirken görülen gerekçe",
        )
        # Karar verilmiş kaydın eksik gerekçesi yargılanmadan, eski yoldan tamamlanır.
        assert kayit["F0"].gerekce_metni == "F0 uygun." and kayit["F2"].gerekce_metni == "F2 uygun."
        assert kayit["F3"].uygunluk == UYGUN_DEGIL

    senaryo(adimlar)


def test_karar_gerekceyle_birlikte_sifirlanir_ve_yeniden_yargilanir(yargici):
    async def adimlar(istemci, d):
        aday, *_ = await _firmalar(d, 2)
        ilan = await _ortak_ilan(d)
        yargici.kur({"F0": UYGUN_DEGIL})
        assert await _listelenenler(d, ilan) == ["F1"]
        kart_id = aday.kart.id

        await firma_servisi.onerilerin_gerekcesini_bosalt(d.oturum, kart_id)
        await d.oturum.commit()
        assert (await _kayitlar(d, ilan))["F0"].uygunluk is None

        y = yargici.kur({"F0": KISMEN})
        assert sorted(await _listelenenler(d, ilan)) == ["F0", "F1"]
        assert y.cagrilar == ["F0"]  # yalnızca sıfırlanan aday

    senaryo(adimlar)


def test_eski_gerekceli_kararsiz_kayit_yeniden_yargilanir(yargici):
    """Migration öncesi kayıt: gerekçesi var, kararı yok → bir kez yargılanır, sonra kalır."""

    async def adimlar(istemci, d):
        await _firmalar(d, 2)
        ilan = await _ortak_ilan(d)
        yargici.kur()
        await _listelenenler(d, ilan)
        kayit = await _kayitlar(d, ilan)
        kayit["F0"].uygunluk, kayit["F0"].gerekce_metni = None, "eski gerekçe"
        await d.oturum.commit()

        y = yargici.kur({"F0": UYGUN_DEGIL})
        assert await _listelenenler(d, ilan) == ["F1"]
        assert y.cagrilar == ["F0"]
        assert (await _kayitlar(d, ilan))["F0"].uygunluk == UYGUN_DEGIL

    senaryo(adimlar)


def test_basarisiz_yargi_eski_gerekceyi_silmez(yargici):
    async def adimlar(istemci, d):
        await _firmalar(d, 1)
        ilan = await _ortak_ilan(d)
        yargici.kur()
        await _listelenenler(d, ilan)
        kayit = (await _kayitlar(d, ilan))["F0"]
        kayit.uygunluk, kayit.gerekce_metni = None, "eski gerekçe"
        await d.oturum.commit()

        yargici.kur({"F0": RuntimeError})
        assert await _listelenenler(d, ilan) == ["F0"]
        assert (await _kayitlar(d, ilan))["F0"].gerekce_metni == "eski gerekçe"

    senaryo(adimlar)


def _yeni_aday_bildirimleri(d, ilan):
    return d.oturum.scalars(
        select(Bildirim.metin).where(
            Bildirim.hesap_id == d.kurum1.hesap.id, Bildirim.tur == TUR_YENI_ONERI
        )
    )


def test_uygun_degil_icin_yeni_aday_bildirimi_yazilmaz(yargici):
    async def adimlar(istemci, d):
        await _firmalar(d, 3)
        ilan = await _ortak_ilan(d)
        yargici.kur({"F0": UYGUN_DEGIL, "F1": UYGUN_DEGIL, "F2": KISMEN})
        await _listelenenler(d, ilan)
        # Üç kayıt yazıldı, görünür olan tek: bildirim yalnızca onu sayar.
        assert list(await _yeni_aday_bildirimleri(d, ilan)) == ["İhtiyacınız için 1 yeni aday var."]

    senaryo(adimlar)


def test_hepsi_elenince_bildirim_yok(yargici):
    async def adimlar(istemci, d):
        await _firmalar(d, 2)
        ilan = await _ortak_ilan(d)
        yargici.kur(varsayilan=UYGUN_DEGIL)
        assert await _listelenenler(d, ilan) == []
        assert list(await _yeni_aday_bildirimleri(d, ilan)) == []
        assert len(await _kayitlar(d, ilan)) == 2  # saklandı

    senaryo(adimlar)


def test_genc_ilani_yargilanmaz(yargici, monkeypatch):
    """Kapsam yalnızca firma–firma: genç ilanında yargı çağrısı hiç yapılmaz."""

    async def adimlar(istemci, d):
        y = yargici.kur(varsayilan=UYGUN_DEGIL)
        genc_ilani = IhtiyacKarti(
            kurum_id=d.kurum1.profil.id, problem_tanimi="Genç ilanı", embedding=[1.0] + [0.0] * 1023
        )
        d.oturum.add(genc_ilani)
        await d.oturum.commit()

        async def gerekce(ihtiyac, aday):
            return "gerekçe"

        monkeypatch.setattr(servis, "gerekce_uret", gerekce)
        await servis.pipeline_calistir(d.oturum, genc_ilani)
        assert y.cagrilar == []

    senaryo(adimlar)


# --- Okuma uçları: uygun_degil hiçbir yerde görünmez -----------------------------------


async def _gizli_kurulum(d):
    """F0 uygun, F1 uygun_degil (gizli), F2 kısmen. Döner: (ilan, kayıtlar, firmalar)."""
    firmalar = await _firmalar(d, 3)
    ilan = await _ortak_ilan(d)
    await servis.pipeline_calistir(d.oturum, ilan)
    kayit = await _kayitlar(d, ilan)
    kayit["F1"].uygunluk = UYGUN_DEGIL
    kayit["F2"].uygunluk = KISMEN
    await d.oturum.commit()
    return ilan, kayit, firmalar


def test_oneriler_ucu_gizliyi_gostermez_kismeni_rozetle_gosterir():
    async def adimlar(istemci, d):
        ilan, kayit, _ = await _gizli_kurulum(d)
        yanit = await istemci.get(
            f"/eslestirme/oneriler/{d.kurum1.profil.id}",
            params={"ihtiyac_karti_id": str(ilan.id)},
            headers=d.kurum1.baslik,
        )
        assert yanit.status_code == 200
        oneriler = yanit.json()["oneriler"]
        assert sorted(o["firma_karti"]["firma_adi"] for o in oneriler) == ["F0", "F2"]
        assert {o["firma_karti"]["firma_adi"]: o["uygunluk"] for o in oneriler} == {
            "F0": UYGUN,
            "F2": KISMEN,
        }
        # GİRVAK da aynı okuma ucundan gizliyi görmez.
        girvak = await istemci.get(
            f"/eslestirme/oneriler/{d.kurum1.profil.id}",
            params={"ihtiyac_karti_id": str(ilan.id)},
            headers=d.girvak.baslik,
        )
        assert len(girvak.json()["oneriler"]) == 2

    senaryo(adimlar)


def test_yalnizca_gizli_kayit_varsa_oneriler_ucu_hesaplamaz(yargici):
    async def adimlar(istemci, d):
        await _firmalar(d, 2)
        ilan = await _ortak_ilan(d)
        y = yargici.kur(varsayilan=UYGUN_DEGIL)
        await servis.pipeline_calistir(d.oturum, ilan)
        onceki = len(y.cagrilar)

        yanit = await istemci.get(
            f"/eslestirme/oneriler/{d.kurum1.profil.id}",
            params={"ihtiyac_karti_id": str(ilan.id)},
            headers=d.kurum1.baslik,
        )
        assert yanit.status_code == 200 and yanit.json()["oneriler"] == []
        assert len(y.cagrilar) == onceki  # gizli kayıtlar "hesaplanmış" demek

    senaryo(adimlar)


def test_onerilerim_ucu_gizliyi_gostermez():
    async def adimlar(istemci, d):
        await _gizli_kurulum(d)
        yanit = await istemci.get("/eslestirme/onerilerim", headers=d.kurum1.baslik)
        firmalar = [o["aday_adi"] for o in yanit.json() if o["aday_turu"] == "firma"]
        assert sorted(firmalar) == ["F0", "F2"]

    senaryo(adimlar)


def test_aday_firmanin_firsatlari_gizliyi_gostermez():
    async def adimlar(istemci, d):
        _, _, firmalar = await _gizli_kurulum(d)
        gorunen = await istemci.get("/eslestirme/firma-eslesmelerim", headers=firmalar[0].baslik)
        assert len(gorunen.json()) == 1
        assert gorunen.json()[0]["uygunluk"] == UYGUN
        kismen = await istemci.get("/eslestirme/firma-eslesmelerim", headers=firmalar[2].baslik)
        assert kismen.json()[0]["uygunluk"] == KISMEN
        gizli = await istemci.get("/eslestirme/firma-eslesmelerim", headers=firmalar[1].baslik)
        assert gizli.status_code == 200 and gizli.json() == []

    senaryo(adimlar)


def test_gizli_kayit_hicbir_gecis_ucundan_acilmaz():
    """Kimlik bilinse bile 404: ne ilan sahibi ne aday firma gizli kaydı değiştirebilir."""

    async def adimlar(istemci, d):
        ilan, kayit, firmalar = await _gizli_kurulum(d)
        eid = kayit["F1"].id
        aday = firmalar[1].baslik
        for yol, baslik, govde in (
            ("/eslestirme/ilgileniyorum", d.kurum1.baslik, {"eslesme_id": str(eid)}),
            (f"/eslestirme/{eid}/simdilik-degil", d.kurum1.baslik, None),
            (f"/eslestirme/{eid}/firma-ilgi", aday, {"iletisim_onayi": True}),
            (f"/eslestirme/{eid}/firma-ilgiyi-geri-cek", aday, None),
            (f"/eslestirme/{eid}/firma-kabul", aday, None),
            (f"/eslestirme/{eid}/firma-red", aday, None),
        ):
            yanit = await istemci.post(yol, headers=baslik, **({"json": govde} if govde else {}))
            assert yanit.status_code == 404, yol
        assert (await _kayitlar(d, ilan))["F1"].durum == "onerildi"
        # Aynı uç görünür kayıtta çalışır (kontrol).
        gorunen = await istemci.post(
            f"/eslestirme/{kayit['F0'].id}/firma-ilgi",
            headers=firmalar[0].baslik,
            json={"iletisim_onayi": True},
        )
        assert gorunen.status_code == 200

    senaryo(adimlar)


def test_gizli_kayit_ilan_gorme_hakki_vermez():
    async def adimlar(istemci, d):
        ilan, _, firmalar = await _gizli_kurulum(d)
        yol = f"/ihtiyac-kartlari/{ilan.id}"
        assert (await istemci.get(yol, headers=firmalar[0].baslik)).status_code == 200
        assert (await istemci.get(yol, headers=firmalar[1].baslik)).status_code == 404

    senaryo(adimlar)


def test_girvak_sayilari_gizliyi_saymaz():
    async def adimlar(istemci, d):
        await _gizli_kurulum(d)
        gorunen_onerildi = await d.oturum.scalar(
            select(func.count()).where(Eslesme.durum == "onerildi", gorunur_kosulu())
        )
        gizli = await d.oturum.scalar(select(func.count()).where(Eslesme.uygunluk == UYGUN_DEGIL))
        assert gizli >= 1
        gorunen_firma = await d.oturum.scalar(
            select(func.count()).where(
                Eslesme.durum == "onerildi",
                Eslesme.firma_karti_id.isnot(None),
                gorunur_kosulu(),
            )
        )
        yanit = await istemci.get("/girvak/sayilar", headers=d.girvak.baslik)
        govde = yanit.json()
        assert govde["eslesme"]["onerildi"] == gorunen_onerildi
        assert govde["kirilim"]["firma_firma"]["oneri"] == gorunen_firma

    senaryo(adimlar)


def test_genc_uclari_da_ayni_filtreyi_kullanir():
    """Genç eşleşmesi bugün yargılanmıyor, ama filtre her okuma ucunda: işaretli kayıt görünmez."""

    async def adimlar(istemci, d):
        ilan = IhtiyacKarti(kurum_id=d.kurum1.profil.id, problem_tanimi="Genç ilanı")
        d.oturum.add(ilan)
        await d.oturum.flush()
        eslesme = Eslesme(
            ihtiyac_karti_id=ilan.id, yetenek_karti_id=d.K1.id, skor=0.7, durum="onerildi"
        )
        d.oturum.add(eslesme)
        await d.oturum.commit()

        async def firsatlar():
            yanit = await istemci.get("/eslestirme/firsatlarim", headers=d.genc1.baslik)
            return [f["eslesme_id"] for f in yanit.json() if f["eslesme_id"] == str(eslesme.id)]

        async def durum_ver(durum, baslatan, uygunluk):
            e = await d.oturum.get(Eslesme, eslesme.id)
            e.durum, e.baslatan, e.uygunluk = durum, baslatan, uygunluk
            await d.oturum.commit()

        async def liste(yol):
            yanit = await istemci.get(yol, headers=d.genc1.baslik)
            return [f["eslesme_id"] for f in yanit.json() if f["eslesme_id"] == str(eslesme.id)]

        # fırsatlarım
        assert await firsatlar() == [str(eslesme.id)]  # kontrol: işaretsiz görünür
        await durum_ver("onerildi", None, UYGUN_DEGIL)
        assert await firsatlar() == []
        # ilgilerim (genç ilgilendi)
        await durum_ver("genc_ilgilendi", TARAF_ADAY, None)
        assert await liste("/eslestirme/ilgilerim") == [str(eslesme.id)]
        await durum_ver("genc_ilgilendi", TARAF_ADAY, UYGUN_DEGIL)
        assert await liste("/eslestirme/ilgilerim") == []
        # bana gelenler (firma ilgilendi)
        await durum_ver("ilgileniliyor", TARAF_ILAN, None)
        assert await liste("/eslestirme/bana-gelenler") == [str(eslesme.id)]
        await durum_ver("ilgileniliyor", TARAF_ILAN, UYGUN_DEGIL)
        assert await liste("/eslestirme/bana-gelenler") == []
        # geçiş uçları
        for yol in ("kabul", "red", "genc-ilgi", "ilgiyi-geri-cek"):
            kod = (
                await istemci.post(
                    f"/eslestirme/{eslesme.id}/{yol}",
                    headers=d.genc1.baslik,
                    json={"iletisim_onayi": True},
                )
            ).status_code
            assert kod == 404, yol

    senaryo(adimlar)
