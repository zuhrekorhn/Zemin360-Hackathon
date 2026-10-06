"""Eşleştirme Ajanı'nın skor ve eleme mantığı — LLM ve veritabanı olmadan.

Formül ve benzerlik tabanı docs/matching-algorithm.md § 4-5'ten geliyor.
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
    FIRMA_BENZERLIK_ALT_SINIRI,
    TOP_N,
    FirmaAdayi,
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
    alt_sinir: float = BENZERLIK_ALT_SINIRI

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


def test_bos_baslik_bonusu_dusurmez():
    """Referans eklemek kartı zayıflatmamalı (bulgu 17): linksiz kalemde yalnızca
    Referans doluysa (—, —, —, 3) oran 1.0; eskiden (0, 0, 0, 3) = 0.25 sayılıyordu."""
    tam = (3, 3, 3, None)
    assert dogrulama_bonusu([tam]) == 1.0
    assert dogrulama_bonusu([tam, (None, None, None, 3)]) == 1.0


def test_bos_baslik_oranin_paydasina_girmez():
    # (3 + 2 + 1) / (3 × 3) = 2/3
    assert dogrulama_bonusu([(3, 2, 1, None)]) == pytest.approx(2 / 3)


def test_hic_dolu_basligi_olmayan_gosterge_ortalamaya_girmez():
    assert dogrulama_bonusu([(3, 3, 3, 3), (None, None, None, None)]) == 1.0
    assert dogrulama_bonusu([(None, None, None, None)]) == 0.0


def test_skor_formulu_belgedeki_agirliklari_kullanir():
    # 0.75 * 0.8 + 0.25 * 0.5 = 0.725
    assert skor_hesapla(0.8, 0.5) == pytest.approx(0.725)


def test_dogrulanmis_kart_esit_benzerlikte_one_gecer():
    dogrulanmis = SahteAday("dogrulanmis", benzerlik=0.70, dogrulama_bonus=0.8)
    ham = SahteAday("ham", benzerlik=0.70)
    assert siralayip_ele([ham, dogrulanmis])[0].ad == "dogrulanmis"


def test_benzerlik_tabaninin_altindaki_aday_hic_gosterilmez():
    """Eskiden bu test skor eşiğini (%40) sınıyordu; eşik kalktı, giriş kararı
    yalnızca benzerlik tabanında. Aynı aday (0.30) hâlâ elenir, sebebi artık tabandır."""
    zayif = SahteAday("zayif", benzerlik=0.30)
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
    0.75*0.34 + 0.25*0.75 = 0.44 skor alıyordu — konuyla ilgisi yokken. Skor
    eşiği kalktı; bonus giriş kararına hiç karışmıyor.
    """
    alakasiz = SahteAday("alakasiz", benzerlik=0.34, dogrulama_bonus=0.75)
    assert alakasiz.skor > skor_hesapla(BENZERLIK_ALT_SINIRI, 0.0)  # skoru yüksek…
    assert siralayip_ele([alakasiz]) == []  # …ama alaka tabanında elenir


def test_alt_sinirin_ustundeki_aday_kalir():
    sinirda = SahteAday("sinirda", benzerlik=BENZERLIK_ALT_SINIRI, dogrulama_bonus=0.5)
    assert siralayip_ele([sinirda]) == [sinirda]


def test_alaka_elemesi_bonustan_bagimsiz():
    """Aynı benzerlikteki iki aday, bonusları farklı olsa da aynı kararı alır."""
    ham = SahteAday("ham", benzerlik=0.30)
    dogrulanmis = SahteAday("dogrulanmis", benzerlik=0.30, dogrulama_bonus=1.0)
    assert siralayip_ele([ham, dogrulanmis]) == []


def test_listeye_girme_karari_yalnizca_benzerlige_baglidir():
    """Aynı benzerlikte, bonusu 0 ve 1 olan iki kart aynı kararı alır; bonus yalnızca sıralar.

    Eski kuralda bonusu 0 olan kart 0.45-0.53 bandında %40 eşiğine takılıp
    düşüyor, bonusu 1 olan aynı benzerlikteki kart giriyordu.
    """
    for benzerlik in (BENZERLIK_ALT_SINIRI - 0.01, BENZERLIK_ALT_SINIRI, 0.50, 0.65):
        ham = SahteAday("ham", benzerlik=benzerlik, dogrulama_bonus=0.0)
        tam = SahteAday("tam", benzerlik=benzerlik, dogrulama_bonus=1.0)
        girdi_ham = siralayip_ele([ham]) == [ham]
        girdi_tam = siralayip_ele([tam]) == [tam]
        assert girdi_ham == girdi_tam == (benzerlik >= BENZERLIK_ALT_SINIRI)


def test_bonus_yalnizca_siralamayi_degistirir():
    ham = SahteAday("ham", benzerlik=0.50, dogrulama_bonus=0.0)
    tam = SahteAday("tam", benzerlik=0.50, dogrulama_bonus=1.0)
    # Tabanın hemen üstündeki kanıtsız aday artık listeden düşmüyor (skoru 0.375 < 0.40 idi).
    assert [a.ad for a in siralayip_ele([ham, tam])] == ["tam", "ham"]


def test_alaka_tabani_belgedeki_degerde_ve_gurultunun_ustunde():
    assert benzerlik_yeterli_mi(BENZERLIK_ALT_SINIRI) is True
    assert benzerlik_yeterli_mi(BENZERLIK_ALT_SINIRI - 0.01) is False
    assert BENZERLIK_ALT_SINIRI == 0.48
    # Gözlenen alakasız küme 0.27-0.36 bandındaydı; sınır onun üstünde kalmalı.
    assert BENZERLIK_ALT_SINIRI > 0.36


def test_firma_tabani_ayri_sabit_ve_firma_adayina_o_uygulanir():
    """Firma tabanı şimdilik 0.48 ama ayrı sabit (firma metinleri için ölçülmedi)."""
    assert FIRMA_BENZERLIK_ALT_SINIRI == 0.48
    tabanda = FirmaAdayi(
        firma_karti=None, benzerlik=FIRMA_BENZERLIK_ALT_SINIRI, dogrulama_bonus=0.0
    )
    assert siralayip_ele([tabanda]) == [tabanda]
    # Bonus ne kadar yüksek olursa olsun tabanın altındaki firma adayı elenir.
    altinda = FirmaAdayi(
        firma_karti=None, benzerlik=FIRMA_BENZERLIK_ALT_SINIRI - 0.01, dogrulama_bonus=1.0
    )
    assert siralayip_ele([altinda]) == []


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
