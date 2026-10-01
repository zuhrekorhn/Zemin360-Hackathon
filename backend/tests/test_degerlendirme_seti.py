"""Değerlendirme setinin bütünlüğü ve bugünkü sistemin gerileme anlık görüntüsü.

Gerileme testi karneyi ayrı bir süreçte, çevrimdışı (kasetle) üretir ve
`karneler/mevcut_sistem.json` ile karşılaştırır. Ayrı süreç şart: bugünkü
başlık ayrıştırması iki vakada süre sınırına takılıyor ve işçi süreç
öldürülüyor; test sürecini etkilememeli.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from degerlendirme.kaset import AgKaseti, KasetKipi
from degerlendirme.mevcut_sistem import eski_olcege_cevir
from degerlendirme.vaka import (
    SETI_KLASORU,
    Alan,
    ReferansGirdisi,
    Vaka,
    VakaDosyasiHatasi,
    vakalari_yukle,
)

BACKEND = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def vakalar() -> list[Vaka]:
    return vakalari_yukle()


def test_her_alanda_vaka_var(vakalar):
    assert {v.alan for v in vakalar} == set(Alan)


def test_en_az_on_bireysel_vaka_var(vakalar):
    assert sum(v.bireysel for v in vakalar) >= 10


def test_her_link_kasette_kayitli(vakalar):
    kaset = AgKaseti(KasetKipi.OYNAT)
    eksik = [(v.id, link) for v in vakalar for link in v.linkler if not kaset.kayitli_mi(link)]
    assert not eksik, f"kaydedilmemiş linkler (python -m scripts.karne --kip kaydet): {eksik}"


def test_dosya_kanitlari_mevcut(vakalar):
    eksik = [
        k.dosya
        for v in vakalar
        for k in v.kanitlar
        if k.dosya and not (SETI_KLASORU / "dosyalar" / k.dosya).exists()
    ]
    assert not eksik


def test_etiket_etiketleyensiz_gecersiz():
    with pytest.raises(ValueError, match="etiketleyeni yok"):
        Vaka.model_validate(
            {
                "id": "v",
                "alan": "yazilim",
                "amac": "x",
                "iddia": {"baslik": "b"},
                "kimlik": {"ad": "a", "eposta": "e@ornek.com"},
                "beklenen": {"kanit": 2, "sonuc": 2, "rol": 2, "referans": None},
            }
        )


@pytest.mark.parametrize(
    "hatali",
    [
        {"kanitlar": [{"tur": "link"}]},  # url yok
        {"kanitlar": [{"tur": "dosya", "url": "https://x.com"}]},  # dosya yolu yok
        {"onerilen": {"kanit": 4, "sonuc": 0, "rol": 0, "referans": None}},  # aralık dışı
        {"bilinmeyen_alan": 1},  # yazım hatası sessizce yutulmaz
    ],
)
def test_hatali_vaka_reddedilir(hatali):
    temel = {
        "id": "v",
        "alan": "yazilim",
        "amac": "x",
        "iddia": {"baslik": "b"},
        "kimlik": {"ad": "a", "eposta": "e@ornek.com"},
    }
    with pytest.raises(ValueError):
        Vaka.model_validate({**temel, **hatali})


def test_tekrarlanan_kimlik_reddedilir(tmp_path):
    vaka = (
        "- {id: v, alan: yazilim, amac: x, iddia: {baslik: b},"
        " kimlik: {ad: a, eposta: e@ornek.com}}\n"
    )
    (tmp_path / "a.yaml").write_text(vaka, encoding="utf-8")
    (tmp_path / "b.yaml").write_text(vaka, encoding="utf-8")
    with pytest.raises(VakaDosyasiHatasi, match="tekrarlanan"):
        vakalari_yukle(tmp_path)


@pytest.mark.parametrize(
    ("yanitlar", "eski"),
    [
        (("evet", "evet", "evet"), 5),
        (("kismen", "hayir", "bilmiyorum"), 2),  # (3 + 1) / 2
        (("bilmiyorum", "bilmiyorum", None), 3),
    ],
)
def test_dort_soruluk_yanit_eski_olcege_cevrilir(yanitlar, eski):
    referans = ReferansGirdisi(
        eposta="r@ornek.com",
        iliski="yonetici",
        iddia_dogru=yanitlar[0],
        pay_dogru=yanitlar[1],
        sonuc_dogru=yanitlar[2],
    )
    assert eski_olcege_cevir(referans) == eski


def test_bugunku_sistem_karnesi_degismedi(tmp_path):
    """Davranışı değiştirmemesi gereken her adım bu testi değiştirmeden geçmeli."""
    cikti = tmp_path / "sonuclar.json"
    tamam = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.karne",
            "--taslak",
            "--rapor-yazma",
            "--ayristirma-suresi",
            "5",
            "--json",
            str(cikti),
        ],
        cwd=BACKEND,
        capture_output=True,
        timeout=180,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert tamam.returncode == 0, tamam.stderr.decode("utf-8", "replace")[-2000:]
    beklenen = json.loads((SETI_KLASORU / "karneler" / "mevcut_sistem.json").read_text("utf-8"))
    assert json.loads(cikti.read_text("utf-8")) == beklenen
