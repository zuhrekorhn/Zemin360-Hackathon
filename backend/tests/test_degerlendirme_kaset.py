"""Kaset: kayıt ve oynatma ağı ve modeli birebir yeniden üretmeli (degerlendirme/kaset.py)."""

import asyncio
import json

import httpx
import pytest

from app.core import guvenli_istek
from degerlendirme.kaset import (
    AKIS_PARCASI,
    AgKaseti,
    KasetEksik,
    KasetKipi,
    ModelKaseti,
    istek_anahtari,
)


def _yaz(klasor, dns=None, ag=None, model=None):
    (klasor / "govdeler").mkdir(parents=True, exist_ok=True)
    for ad, veri in (("dns.json", dns), ("ag.json", ag), ("model.json", model)):
        if veri is not None:
            (klasor / ad).write_text(json.dumps(veri), encoding="utf-8")


def test_istek_anahtari_ipye_sabitlenmis_istekte_host_basligini_kullanir():
    istek = httpx.Request("GET", "https://93.184.216.34/a/b?x=1", headers={"Host": "ornek.com"})
    assert istek_anahtari(istek) == "GET https://ornek.com/a/b?x=1"


def test_oynatma_kayitli_govdeyi_parca_parca_akitir(tmp_path):
    import gzip

    govde = b"x" * (AKIS_PARCASI * 2 + 10)
    (tmp_path / "govdeler").mkdir()
    (tmp_path / "govdeler" / "g.gz").write_bytes(gzip.compress(govde))
    _yaz(tmp_path, ag={"GET https://ornek.com/": {"durum": 200, "basliklar": {}, "govde": "g.gz"}})
    kaset = AgKaseti(KasetKipi.OYNAT, tmp_path)

    async def oku():
        async with httpx.AsyncClient(transport=kaset.transport()) as istemci:
            async with istemci.stream("GET", "https://ornek.com/") as yanit:
                return [len(p) async for p in yanit.aiter_bytes()]

    parcalar = asyncio.run(oku())
    assert sum(parcalar) == len(govde)
    assert len(parcalar) == 3  # tek parça değil: okuyucunun "ilk N bayt" mantığı gerçekteki gibi


def test_kayitta_olmayan_istek_kaset_eksik(tmp_path):
    _yaz(tmp_path, ag={})
    kaset = AgKaseti(KasetKipi.OYNAT, tmp_path)

    async def iste():
        async with httpx.AsyncClient(transport=kaset.transport()) as istemci:
            await istemci.get("https://kayitsiz.com/")

    with pytest.raises(KasetEksik):
        asyncio.run(iste())


def test_kaydedilen_ag_hatasinin_turu_aynen_uretilir(tmp_path):
    _yaz(tmp_path, ag={"GET https://yavas.com/": {"hata": "ConnectTimeout"}})
    kaset = AgKaseti(KasetKipi.OYNAT, tmp_path)

    async def iste():
        async with httpx.AsyncClient(transport=kaset.transport()) as istemci:
            await istemci.get("https://yavas.com/")

    with pytest.raises(httpx.ConnectTimeout):
        asyncio.run(iste())


def test_dns_kaydi_cozulemedi_ise_oserror_ve_baglam_geri_alinir(tmp_path):
    _yaz(tmp_path, dns={"yok.com": None, "var.com": ["93.184.216.34"]})
    kaset = AgKaseti(KasetKipi.OYNAT, tmp_path)
    onceki = guvenli_istek.cozumleyici
    with kaset.dns_baglami():
        assert guvenli_istek.cozumleyici == kaset.cozumle
        assert [str(ip) for ip in asyncio.run(kaset.cozumle("var.com", 443))] == ["93.184.216.34"]
        with pytest.raises(OSError):
            asyncio.run(kaset.cozumle("yok.com", 443))
        with pytest.raises(KasetEksik):
            asyncio.run(kaset.cozumle("hic.com", 443))
    assert guvenli_istek.cozumleyici is onceki


def test_model_kaseti_oynatir_ve_eksikte_hata_verir(tmp_path):
    anahtar = ModelKaseti.anahtar("is", {"a": 1})
    _yaz(tmp_path, model={anahtar: {"sonuc": 7}})
    kaset = ModelKaseti(KasetKipi.OYNAT, tmp_path)

    async def gercek():
        raise AssertionError("oynatmada gerçek çağrı yapılmamalı")

    assert asyncio.run(kaset.cagir("is", {"a": 1}, gercek)) == {"sonuc": 7}
    with pytest.raises(KasetEksik):
        asyncio.run(kaset.cagir("is", {"a": 2}, gercek))


def test_model_kaydi_yalnizca_kullanilanlari_yazar_ve_eskiyi_yeniden_cagirmaz(tmp_path):
    eski = ModelKaseti.anahtar("is", {"a": 1})
    kullanilmayan = ModelKaseti.anahtar("is", {"a": 99})
    _yaz(tmp_path, model={eski: {"sonuc": 1}, kullanilmayan: {"sonuc": 0}})
    kaset = ModelKaseti(KasetKipi.KAYDET, tmp_path)
    cagrilar = []

    async def gercek():
        cagrilar.append(1)
        return {"sonuc": 2}

    asyncio.run(kaset.cagir("is", {"a": 1}, gercek))  # kayıtlı: çağrılmaz
    asyncio.run(kaset.cagir("is", {"a": 2}, gercek))  # yeni: çağrılır
    kaset.kaydet()

    yazilan = json.loads((tmp_path / "model.json").read_text(encoding="utf-8"))
    assert len(cagrilar) == 1
    assert set(yazilan) == {eski, ModelKaseti.anahtar("is", {"a": 2})}
