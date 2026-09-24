"""Eşleştirme Ajanı'nın skor ve eleme mantığı — LLM ve veritabanı olmadan.

Formül ve eşikler docs/matching-algorithm.md § 4-5'ten geliyor.
"""

from dataclasses import dataclass

import pytest

from app.agents.eslestirme import (
    SKOR_ESIGI,
    TOP_N,
    dogrulama_bonusu,
    siralayip_ele,
    skor_hesapla,
)


@dataclass(frozen=True)
class SahteAday:
    """Aday'ın test için yeterli yüzü: skor hesabı benzerlik + bonustan çıkar."""

    ad: str
    benzerlik: float
    dogrulama_bonus: float = 0.0

    @property
    def skor(self) -> float:
        return skor_hesapla(self.benzerlik, self.dogrulama_bonus)


def test_dogrulama_skoru_olmayan_kart_sifir_bonus_alir():
    """Kanıtsız kart cezalandırılmaz, sadece bonus almaz (§ 4)."""
    assert dogrulama_bonusu([]) == 0.0


def test_tam_guven_skoru_bir_bonus_verir():
    assert dogrulama_bonusu([(3, 3, 3, 3)]) == 1.0


def test_birden_fazla_cikti_ortalamasi_alinir():
    # (12/12 + 6/12) / 2 = 0.75
    assert dogrulama_bonusu([(3, 3, 3, 3), (2, 2, 1, 1)]) == pytest.approx(0.75)


def test_skor_formulu_belgedeki_agirliklari_kullanir():
    # 0.75 * 0.8 + 0.25 * 0.5 = 0.725
    assert skor_hesapla(0.8, 0.5) == pytest.approx(0.725)


def test_dogrulanmis_kart_esit_benzerlikte_one_gecer():
    dogrulanmis = SahteAday("dogrulanmis", benzerlik=0.70, dogrulama_bonus=0.8)
    ham = SahteAday("ham", benzerlik=0.70)
    assert siralayip_ele([ham, dogrulanmis])[0].ad == "dogrulanmis"


def test_esik_altindaki_aday_hic_gosterilmez():
    zayif = SahteAday("zayif", benzerlik=0.30)  # 0.225 < 0.40
    assert zayif.skor < SKOR_ESIGI
    assert siralayip_ele([zayif]) == []


def test_en_fazla_bes_sonuc_doner():
    adaylar = [SahteAday(f"aday-{i}", benzerlik=0.9 - i * 0.01) for i in range(9)]
    secilenler = siralayip_ele(adaylar)
    assert len(secilenler) == TOP_N
    # Sıralama skora göre azalan olmalı
    assert [a.ad for a in secilenler] == [f"aday-{i}" for i in range(TOP_N)]


def test_bos_havuz_bos_liste_dondurur():
    assert siralayip_ele([]) == []
