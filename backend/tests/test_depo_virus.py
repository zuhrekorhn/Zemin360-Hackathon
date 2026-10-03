"""Dosya deposu ve virüs tarayıcı adaptörleri (plan § 4.4, § 14.4)."""

import asyncio
import datetime as dt

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.dis_servisler import kurulum
from app.core.dis_servisler.depo import DepoKapali, KapaliDepo, YerelDepo, indirme_basligi
from app.core.dis_servisler.virus import (
    ClamavTarayici,
    KapaliTarayici,
    TaramaSonucu,
    clamd_yanitini_coz,
)
from app.main import app

IMZA = "test-imza-anahtari"


def _ayar(**ayarlar) -> Settings:
    return Settings(_env_file=None, **ayarlar)


def test_yerel_depo_koyar_okur_siler(tmp_path):
    depo = YerelDepo(tmp_path, IMZA, "http://api")

    async def senaryo():
        await depo.koy("kanit/abcdef0123", b"veri", "application/pdf")
        assert await depo.al("kanit/abcdef0123") == b"veri"
        await depo.sil("kanit/abcdef0123")
        await depo.sil("kanit/abcdef0123")  # yoksa sessiz
        assert not (tmp_path / "kanit" / "abcdef0123").exists()

    asyncio.run(senaryo())


@pytest.mark.parametrize("anahtar", ["../disari", "/mutlak/yol0000", "kisa", "BUYUK_harf00"])
def test_yerel_depo_klasor_disina_cikamaz(tmp_path, anahtar):
    with pytest.raises(ValueError):
        YerelDepo(tmp_path, IMZA, "http://api").yol(anahtar)


def test_imzali_adres_token_cozulur_suresi_dolunca_gecmez(tmp_path):
    depo = YerelDepo(tmp_path, IMZA, "http://api/")
    adres = asyncio.run(
        depo.imzali_adres("kanit/abcdef0123", dosya_adi="rapor.pdf", icerik_turu="application/pdf")
    )
    assert adres.startswith("http://api/dosya/")
    assert depo.token_coz(adres.rsplit("/", 1)[1]) == (
        "kanit/abcdef0123",
        "rapor.pdf",
        "application/pdf",
    )
    eski = jwt.encode(
        {
            "amac": "dosya",
            "anahtar": "kanit/abcdef0123",
            "ad": "a",
            "tur": "b",
            "exp": dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1),
        },
        IMZA,
        algorithm="HS256",
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        depo.token_coz(eski)


def test_indirme_basligi_turkce_adi_kodlar():
    baslik = indirme_basligi('Çalışma "rapor".pdf')
    assert baslik.startswith('attachment; filename="alma rapor.pdf"')
    assert "filename*=UTF-8''%C3%87al%C4%B1%C5%9Fma" in baslik


def test_indirme_ucu_dosyayi_ek_olarak_verir(tmp_path, monkeypatch):
    depo = YerelDepo(tmp_path, IMZA, "http://testserver")
    monkeypatch.setattr(kurulum, "depo", lambda: depo)
    asyncio.run(depo.koy("kanit/abcdef0123", b"%PDF-1.4", "application/pdf"))
    adres = asyncio.run(
        depo.imzali_adres("kanit/abcdef0123", dosya_adi="rapor.pdf", icerik_turu="application/pdf")
    )
    istemci = TestClient(app)
    yanit = istemci.get(adres.replace("http://testserver", ""))
    assert yanit.status_code == 200
    assert yanit.content == b"%PDF-1.4"
    assert yanit.headers["content-disposition"].startswith("attachment")
    assert yanit.headers["x-content-type-options"] == "nosniff"
    assert istemci.get("/dosya/bozuk-token").status_code == 404


def test_indirme_ucu_yerel_depo_degilse_404(monkeypatch):
    monkeypatch.setattr(kurulum, "depo", lambda: KapaliDepo())
    assert TestClient(app).get("/dosya/herhangi").status_code == 404


def test_kapali_depo_yuklemeyi_reddeder_silmeyi_yutar():
    depo = KapaliDepo()
    with pytest.raises(DepoKapali):
        asyncio.run(depo.koy("kanit/abcdef0123", b"", "image/png"))
    asyncio.run(depo.sil("kanit/abcdef0123"))


def test_depo_secimi_bayraga_gore():
    assert kurulum.depo_sec(_ayar(depo_saglayici="kapali")).kip == "kapali"
    assert kurulum.depo_sec(_ayar(depo_saglayici="yerel")).kip == "yerel"
    # R2 ayarı eksikse açılış durmaz, yükleme kapalı kalır.
    assert kurulum.depo_sec(_ayar(depo_saglayici="r2", r2_kova="k")).kip == "kapali"
    tam = _ayar(
        depo_saglayici="r2",
        r2_hesap_kimligi="h",
        r2_erisim_anahtari="e",
        r2_gizli_anahtar="g",
        r2_kova="k",
    )
    assert kurulum.depo_sec(tam).kip == "r2"


@pytest.mark.parametrize(
    ("yanit", "beklenen"),
    [
        (b"stream: OK\0", TaramaSonucu.TEMIZ),
        (b"stream: Eicar-Test-Signature FOUND\0", TaramaSonucu.ZARARLI),
    ],
)
def test_clamd_yaniti(yanit, beklenen):
    assert clamd_yanitini_coz(yanit) is beklenen


def test_clamav_ulasilamazsa_dosya_taranmadan_kabul():
    tarayici = ClamavTarayici("127.0.0.1", 1, zaman_asimi_sn=2)
    assert asyncio.run(tarayici.tara(b"veri")) is TaramaSonucu.TARANMADI


def test_clamav_instream_protokolu():
    """Sahte clamd: parçalı akışı okur, sonuna kadar gelen veride imza arar."""
    alinan = bytearray()

    async def senaryo():
        async def isle(okuyucu, yazici):
            assert await okuyucu.readexactly(10) == b"zINSTREAM\0"
            while True:
                boy = int.from_bytes(await okuyucu.readexactly(4), "big")
                if boy == 0:
                    break
                alinan.extend(await okuyucu.readexactly(boy))
            yazici.write(b"stream: Test FOUND\0" if b"EICAR" in alinan else b"stream: OK\0")
            await yazici.drain()
            yazici.close()

        sunucu = await asyncio.start_server(isle, "127.0.0.1", 0)
        port = sunucu.sockets[0].getsockname()[1]
        async with sunucu:
            return await ClamavTarayici("127.0.0.1", port, 5).tara(b"x" * 70_000 + b"EICAR")

    assert asyncio.run(senaryo()) is TaramaSonucu.ZARARLI
    assert len(alinan) == 70_005


def test_kapali_tarayici_taramaz():
    assert asyncio.run(KapaliTarayici().tara(b"")) is TaramaSonucu.TARANMADI
