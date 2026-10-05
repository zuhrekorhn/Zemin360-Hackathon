"""Haftalık canlı karne: sapma hesabı ve betiğin akışı (ağ ve model çağrılmadan)."""

import asyncio

from degerlendirme.canli import sapma_bolumu, sapmalari_bul
from degerlendirme.degerlendirici import Degerlendirme
from degerlendirme.kaset import KasetKipi
from degerlendirme.olcutler import VakaSonucu
from degerlendirme.vaka import Vaka, vakalari_yukle
from scripts import canli_karne


def _sonuc(kimlik, kanit, *, hata=None, alan="yazilim"):
    vaka = Vaka.model_validate(
        {
            "id": kimlik,
            "alan": alan,
            "amac": "test",
            "iddia": {"baslik": "Bir çalışma"},
            "kimlik": {"ad": "Ad Soyad", "eposta": "a@ornek.com"},
            "beklenen": {"kanit": 2, "sonuc": 2, "rol": 2, "referans": None},
            "etiketleyen": "zuhre",
        }
    )
    return VakaSonucu(vaka, Degerlendirme(kanit, 2, 2, None, hata=hata))


def test_sapma_yalniz_degisen_vakalari_ve_baslik_farkini_verir():
    kayitli = [_sonuc("a", 2), _sonuc("b", 3), _sonuc("c", 1)]
    canli = [_sonuc("a", 2), _sonuc("b", None), _sonuc("c", 1, hata="ConnectError")]
    sapmalar = sapmalari_bul(kayitli, canli)
    assert [s.vaka_id for s in sapmalar] == ["b", "c"]
    assert sapmalar[0].degisen == {"kanit": (3, None)}
    assert sapmalar[1].canli_hata == "ConnectError"
    assert sapmalar[1].degisen == {}  # başlıklar aynı, ama canlıda sonuç üretilemedi


def test_sapma_bolumu_sayiyi_ve_tabloyu_yazar():
    metin = "\n".join(sapma_bolumu(sapmalari_bul([_sonuc("b", 3)], [_sonuc("b", None)]), 1))
    assert "Sapan vaka: **1** / 1" in metin
    assert "| b | yazilim | kanit: 3 → — |" in metin
    assert "Sapan vaka: **0** / 1" in "\n".join(sapma_bolumu([], 1))


def test_kayitli_tur_cevrimdisi_calisir_ve_gecici_klasoru_kullanir(tmp_path):
    vakalar = vakalari_yukle()[:2]
    sonuclar = asyncio.run(canli_karne._calistir(vakalar, KasetKipi.OYNAT, None))
    assert [s.vaka.id for s in sonuclar] == [v.id for v in vakalar]
    assert all(s.degerlendirme.hata is None for s in sonuclar)


def test_betik_karneyi_yazar_sapmayi_gosterir_ve_cikis_kodu_esige_bagli(
    monkeypatch, tmp_path, capsys
):
    """Kayıtlı tur gerçek kasetten (ücretsiz), canlı tur sahte: kayıttan farklı bir Kanıt."""
    gercek = canli_karne._calistir

    async def sahte(vakalar, kip, klasor):
        sonuclar = await gercek(vakalar, KasetKipi.OYNAT, None)
        if kip is not KasetKipi.KAYDET:
            return sonuclar
        # Canlıda ilk vakanın Kanıt'ı okunamaz olsun ("—"): link çürümüş gibi.
        ilk = sonuclar[0]
        yeni = Degerlendirme(
            None, ilk.degerlendirme.sonuc, ilk.degerlendirme.rol, ilk.degerlendirme.referans
        )
        return [VakaSonucu(ilk.vaka, yeni), *sonuclar[1:]]

    monkeypatch.setattr(canli_karne, "_calistir", sahte)
    monkeypatch.setattr(canli_karne, "CANLI_KARNE_KLASORU", tmp_path)
    monkeypatch.setattr(canli_karne, "load_dotenv", lambda: None)
    sonuc = asyncio.run(canli_karne.calistir(["--taslak", "--alan", "yazilim"]))
    cikti = capsys.readouterr().out
    assert "## Kayıttan sapma" in cikti
    assert "## Adalet" in cikti
    assert [d.name for d in tmp_path.iterdir()] == [f"{_bugun()}-canli-taslak-yazilim.md"]
    ilk = next(v for v in vakalari_yukle() if v.alan.value == "yazilim")
    assert f"| {ilk.id} | yazilim | kanit:" in cikti.split("## Kayıttan sapma")[1]
    # Çıkış kodu raporun söylediğiyle aynı: eşikler geçiyorsa 0.
    assert sonuc == (0 if "Kabul eşikleri: **geçiyor**" in cikti else 1)


def _bugun():
    import datetime as dt

    return dt.date.today().isoformat()
