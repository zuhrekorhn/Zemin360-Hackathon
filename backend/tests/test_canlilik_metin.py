"""Canlılık hatırlatma metni (docs/faz-d-canlilik.md § 5) — kişiselleştirme kesilebilir.

Sabitlenenler: her türün şablonu var; LLM metni kurala uymazsa (boş, uzun,
e-posta, girdide olmayan sayı) ya da LLM çökerse şablon gider; tarama
kişisel metni kullanır.
"""

import asyncio
import datetime as dt

import pytest

from app.agents import canlilik
from app.agents.canlilik_kurallari import TURLER
from app.api import canlilik as canlilik_api
from tests.takip_dunyasi import bildirimleri
from tests.test_sahiplik import senaryo

# conftest fixture'ı modül özniteliğini değiştirmeden önce, içe aktarma anında.
GERCEK_KISISEL = canlilik.kisisel_metin


def _baglam(tur="ilgi_yanitsiz_1", alici="genc"):
    return canlilik.HatirlatmaBaglami(
        tur=tur, alici=alici, gun=4, karsi_ad="Koop", adim="Kayıt ekranı", sayi=2, sektor="eğitim"
    )


@pytest.mark.parametrize("tur", TURLER)
@pytest.mark.parametrize("alici", ["genc", "kurum"])
def test_her_turun_sablonu_var_ve_epostasiz(tur, alici):
    metin = canlilik.sablon_metni(_baglam(tur, alici))
    assert metin and "@" not in metin


@pytest.mark.parametrize(
    "metin,gecerli",
    [
        ("Koop 4 gündür yanıtını bekliyor; bir göz atar mısın?", True),
        ("", False),
        ("a" * (canlilik.KISISEL_EN_UZUN + 1), False),
        ("Koop'a koop@ornek.com adresinden yaz.", False),
        ("Koop 5 gündür yanıtını bekliyor.", False),  # 5 girdide yok: uydurma sayı
    ],
)
def test_kisisel_metin_kurali(metin, gecerli):
    assert canlilik.kisisel_metin_gecerli_mi(metin, "Koop 4 Kayıt ekranı 2") is gecerli


def _zincir(monkeypatch, yanit):
    class Sahte:
        async def ainvoke(self, _girdi):
            if isinstance(yanit, Exception):
                raise yanit
            return yanit

    canlilik._kisisel_zincir.cache_clear()
    monkeypatch.setattr(canlilik, "_kisisel_zincir", lambda: Sahte())
    monkeypatch.setattr(canlilik, "kisisel_metin", GERCEK_KISISEL)


def test_kurala_uyan_kisisel_metin_kullanilir(monkeypatch):
    _zincir(monkeypatch, "  Koop 4 gündür\nyanıtını bekliyor; kabul ya da ret, ikisi de olur.  ")
    metin = asyncio.run(canlilik.metin_uret(_baglam()))
    assert metin == "Koop 4 gündür yanıtını bekliyor; kabul ya da ret, ikisi de olur."


@pytest.mark.parametrize(
    "yanit", ["Koop 9 gündür bekliyor.", "", RuntimeError("LLM yok")], ids=["sayi", "bos", "hata"]
)
def test_kullanilamayan_metinde_sablona_duser(monkeypatch, yanit):
    _zincir(monkeypatch, yanit)
    b = _baglam()
    assert asyncio.run(canlilik.metin_uret(b)) == canlilik.sablon_metni(b)


def test_tarama_kisisel_metni_bildirime_yazar(monkeypatch):
    async def kisisel(b):
        return f"Kişisel: {b.karsi_ad} {b.gun}"

    monkeypatch.setattr(canlilik, "kisisel_metin", kisisel)

    async def adimlar(istemci, d):
        d.E2.son_aktivite_tarihi = dt.datetime.now(dt.UTC) - dt.timedelta(days=4)
        await d.oturum.commit()
        await canlilik_api.tarama_yap(d.oturum)
        assert (await bildirimleri(d, d.genc2))[-1].metin == "Kişisel: Koop İki 4"

    senaryo(adimlar)
