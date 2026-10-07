"""Eşleşme durum makinesi — docs/kimlik-ve-dongu.md § 5'teki tablo, birebir.

Her (durum, olay, rol) üçlüsü sınanıyor: tablodaki geçişler, aynı geçişin
tekrarı (yan etkisiz), geçersiz geçişler (409) ve yanlış rol.
"""

import itertools

import pytest

from app.agents.eslesme_durumu import (
    OLAY_ILGILENIYORUM,
    OLAY_KABUL,
    OLAY_RED,
    GecersizGecis,
    GecisSonucu,
    RolUygunDegil,
    gecis,
)

DURUMLAR = ("onerildi", "ilgileniliyor", "kabul_edildi", "reddedildi")
OLAYLAR = (OLAY_ILGILENIYORUM, OLAY_KABUL, OLAY_RED)
ROLLER = ("genc", "kurum", "girvak")

# Notun tablosu: (durum, olay, rol) → yeni durum. Tabloda olmayan her üçlü geçersiz.
GECERLI = {
    ("onerildi", OLAY_ILGILENIYORUM, "kurum"): "ilgileniliyor",
    ("ilgileniliyor", OLAY_KABUL, "genc"): "kabul_edildi",
    ("ilgileniliyor", OLAY_RED, "genc"): "reddedildi",
}
# Aynı geçişin tekrarı: 200, durum aynı, yan etki yok.
TEKRAR = {
    ("ilgileniliyor", OLAY_ILGILENIYORUM, "kurum"): "ilgileniliyor",
    ("kabul_edildi", OLAY_KABUL, "genc"): "kabul_edildi",
    ("reddedildi", OLAY_RED, "genc"): "reddedildi",
}
OLAYIN_ROLU = {OLAY_ILGILENIYORUM: "kurum", OLAY_KABUL: "genc", OLAY_RED: "genc"}


@pytest.mark.parametrize("durum,olay,rol", list(itertools.product(DURUMLAR, OLAYLAR, ROLLER)))
def test_tablo(durum, olay, rol):
    anahtar = (durum, olay, rol)
    if rol != OLAYIN_ROLU[olay]:
        with pytest.raises(RolUygunDegil):
            gecis(durum, olay, rol)
    elif anahtar in GECERLI:
        assert gecis(durum, olay, rol) == GecisSonucu(GECERLI[anahtar], degisti=True)
    elif anahtar in TEKRAR:
        assert gecis(durum, olay, rol) == GecisSonucu(TEKRAR[anahtar], degisti=False)
    else:
        with pytest.raises(GecersizGecis) as hata:
            gecis(durum, olay, rol)
        assert hata.value.durum == durum


@pytest.mark.parametrize(
    "durum,olay",
    [
        ("onerildi", OLAY_KABUL),  # notun örnekleri
        ("reddedildi", OLAY_ILGILENIYORUM),
        ("kabul_edildi", OLAY_RED),
    ],
)
def test_gecersiz_gecis_mevcut_durumu_soyler(durum, olay):
    with pytest.raises(GecersizGecis) as hata:
        gecis(durum, olay, OLAYIN_ROLU[olay])
    assert "şu an" in str(hata.value)


def test_ilgileniyorum_artik_isbirligi_durumuna_gecmez():
    """Eskiden "ilgileniyorum" doğrudan kabul_edildi yapıyordu; artık gencin kabulü gerekir."""
    assert gecis("onerildi", OLAY_ILGILENIYORUM, "kurum").durum == "ilgileniliyor"
