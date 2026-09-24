"""Eşleştirme Ajanı'nın skor ve eleme mantığı — LLM ve veritabanı olmadan.

Formül ve eşikler docs/matching-algorithm.md § 4-5'ten geliyor.
"""

import uuid
from dataclasses import dataclass

import pytest

from app.agents.eslestirme import (
    BENZERLIK_ALT_SINIRI,
    DURUM_ILGILENILIYOR,
    DURUM_KABUL_EDILDI,
    DURUM_ONERILDI,
    DURUM_REDDEDILDI,
    SKOR_ESIGI,
    TOP_N,
    benzerlik_yeterli_mi,
    dogrulama_bonusu,
    siralayip_ele,
    skor_hesapla,
    temizlenecekler,
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


def test_alakasiz_aday_ne_kadar_dogrulanmis_olursa_olsun_elenir():
    """Güven bonusu alakayı yaratmaz (docs/matching-algorithm.md § 5).

    Gerçek veride görülen durum: 0.34 benzerlikli, tam doğrulanmış bir kart
    0.75*0.34 + 0.25*0.75 = 0.44 ile eşiği geçiyordu — konuyla ilgisi yokken.
    """
    alakasiz = SahteAday("alakasiz", benzerlik=0.34, dogrulama_bonus=0.75)
    assert alakasiz.skor >= SKOR_ESIGI  # eski davranışta listeye giriyordu
    assert siralayip_ele([alakasiz]) == []


def test_alt_sinirin_ustundeki_aday_kalir():
    sinirda = SahteAday("sinirda", benzerlik=BENZERLIK_ALT_SINIRI, dogrulama_bonus=0.5)
    assert siralayip_ele([sinirda]) == [sinirda]


def test_alaka_elemesi_bonustan_bagimsiz():
    """Aynı benzerlikteki iki aday, bonusları farklı olsa da aynı kararı alır."""
    ham = SahteAday("ham", benzerlik=0.30)
    dogrulanmis = SahteAday("dogrulanmis", benzerlik=0.30, dogrulama_bonus=1.0)
    assert siralayip_ele([ham, dogrulanmis]) == []


def test_alaka_alt_siniri_esikten_bagimsiz_bir_kural():
    """İki sınır farklı şeyleri ölçüyor; biri diğerinin yerine geçmemeli."""
    assert benzerlik_yeterli_mi(BENZERLIK_ALT_SINIRI) is True
    assert benzerlik_yeterli_mi(BENZERLIK_ALT_SINIRI - 0.01) is False
    # Gözlenen alakasız küme 0.27-0.36 bandındaydı; sınır onun üstünde kalmalı.
    assert BENZERLIK_ALT_SINIRI > 0.36


@dataclass
class SahteEslesme:
    """temizlenecekler()'in gördüğü kadarıyla bir eşleşme kaydı."""

    yetenek_karti_id: uuid.UUID
    durum: str


def test_artik_secilmeyen_oneri_listeden_cikar():
    """Kural değişince eski öneri listede kalmamalı."""
    eskimis = SahteEslesme(uuid.uuid4(), DURUM_ONERILDI)
    assert temizlenecekler([eskimis], secilenler=[]) == [eskimis]


def test_hala_secilen_oneri_korunur():
    kart_id = uuid.uuid4()
    duran = SahteEslesme(kart_id, DURUM_ONERILDI)
    assert temizlenecekler([duran], secilenler=[kart_id]) == []


@pytest.mark.parametrize("durum", [DURUM_ILGILENILIYOR, DURUM_KABUL_EDILDI, DURUM_REDDEDILDI])
def test_kurumun_verdigi_karar_silinmez(durum):
    """Karar verilmiş kayıt artık öneri değil; kural değişse de duruyor."""
    karar = SahteEslesme(uuid.uuid4(), durum)
    assert temizlenecekler([karar], secilenler=[]) == []


def test_temizlik_yalnizca_eskiyenleri_secer():
    kalan_id = uuid.uuid4()
    kalan = SahteEslesme(kalan_id, DURUM_ONERILDI)
    eskimis = SahteEslesme(uuid.uuid4(), DURUM_ONERILDI)
    kabul = SahteEslesme(uuid.uuid4(), DURUM_KABUL_EDILDI)
    assert temizlenecekler([kalan, eskimis, kabul], secilenler=[kalan_id]) == [eskimis]
