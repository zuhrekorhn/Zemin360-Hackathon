"""Doğrulama Ajanı'nın hesap mantığı — LLM ve ağ olmadan.

Sınırlar docs/agent-specs.md § 4 ve docs/sequence-diagrams.md § Akış 2'den.
"""

import datetime as dt

import pytest

from app.agents.dogrulama import (
    DURUM_BEKLIYOR,
    DURUM_YANIT_YOK,
    DURUM_YANITLANDI,
    REFERANS_TIMEOUT_GUN,
    referans_puanina_cevir,
    ucuncu_taraf_onayi_hesapla,
    zaman_asimina_ugradi_mi,
)
from app.models.referans_istegi import ReferansIstegi


def test_referans_skalasi_0_3e_indirgenir():
    assert [referans_puanina_cevir(p) for p in (1, 2, 3, 4, 5)] == [0, 1, 1, 2, 3]


def test_notr_referans_tam_puan_vermez():
    """3 ("ne iyi ne kötü") bir onay değil; tam puan yalnızca 5'te."""
    assert referans_puanina_cevir(3) < referans_puanina_cevir(5)
    assert referans_puanina_cevir(5) == 3


def test_skala_disi_puan_reddedilir():
    with pytest.raises(ValueError):
        referans_puanina_cevir(0)
    with pytest.raises(ValueError):
        referans_puanina_cevir(6)


def test_tek_referans_kendi_puanini_verir():
    assert ucuncu_taraf_onayi_hesapla([4]) == referans_puanina_cevir(4)


def test_cok_referansta_ortalama_alinir():
    """Son yanıt öncekini ezmemeli; hepsi hesaba girer."""
    # 5 -> 3, 2 -> 1 : ortalama 2.0
    assert ucuncu_taraf_onayi_hesapla([5, 2]) == 2


def test_zayif_referans_puani_asagi_ceker():
    """En yükseği almak 'olumlu diyeni bulana kadar sor'u ödüllendirirdi."""
    assert ucuncu_taraf_onayi_hesapla([5, 5, 1]) < ucuncu_taraf_onayi_hesapla([5, 5])


def test_ortalama_normal_yuvarlanir():
    # 5 -> 3, 4 -> 2 : ortalama 2.5, yukarı yuvarlanır (bankacı yuvarlaması değil)
    assert ucuncu_taraf_onayi_hesapla([5, 4]) == 3
    # 3 -> 1, 4 -> 2 : ortalama 1.5 -> 2
    assert ucuncu_taraf_onayi_hesapla([3, 4]) == 2
    # 2 -> 1, 3 -> 1 : ortalama 1.0, olduğu gibi kalır
    assert ucuncu_taraf_onayi_hesapla([2, 3]) == 1


def test_ikinci_guclu_referans_puani_dusurmez():
    """Referans eklemek cezalandırmamalı: 5+4, tek 5'in altına inmemeli."""
    assert ucuncu_taraf_onayi_hesapla([5, 4]) >= ucuncu_taraf_onayi_hesapla([5])


def test_yanitlamis_referans_yoksa_bos():
    """ "Yanıt yok" "—"dur, 0 değil: 0 olumsuz yanıt demek."""
    assert ucuncu_taraf_onayi_hesapla([]) is None


def test_sure_dolmadan_zaman_asimi_yok():
    yeni = dt.datetime.now(dt.UTC) - dt.timedelta(days=REFERANS_TIMEOUT_GUN - 1)
    assert zaman_asimina_ugradi_mi(yeni, DURUM_BEKLIYOR) is False


def test_sure_dolunca_zaman_asimi():
    eski = dt.datetime.now(dt.UTC) - dt.timedelta(days=REFERANS_TIMEOUT_GUN, hours=1)
    assert zaman_asimina_ugradi_mi(eski, DURUM_BEKLIYOR) is True


def test_yanitlanmis_referans_zaman_asimina_ugramaz():
    """Referans cevapladıysa süre dolsa bile durumu değişmemeli."""
    eski = dt.datetime.now(dt.UTC) - dt.timedelta(days=90)
    assert zaman_asimina_ugradi_mi(eski, DURUM_YANITLANDI) is False
    assert zaman_asimina_ugradi_mi(eski, DURUM_YANIT_YOK) is False


def test_zaman_asimi_hesabi_naive_tarihle_de_calisir():
    """Veritabanından tz'siz gelen tarih hesabı bozmamalı."""
    eski = dt.datetime.now(dt.UTC).replace(tzinfo=None) - dt.timedelta(days=30)
    assert zaman_asimina_ugradi_mi(eski, DURUM_BEKLIYOR) is True


# SQLAlchemy kolon varsayılanları nesne oluşturulurken değil INSERT anında
# işliyor; bu yüzden testler kolon tanımındaki varsayılanı doğruluyor.
TOKEN_KOLONU = ReferansIstegi.__table__.c.token
DURUM_KOLONU = ReferansIstegi.__table__.c.durum


def test_token_her_istekte_farkli_ve_tahmin_edilemez():
    uret = TOKEN_KOLONU.default.arg
    tokenlar = {uret(None) for _ in range(20)}
    assert len(tokenlar) == 20
    assert all(len(t) >= 32 for t in tokenlar)


def test_token_tek_kullanimlik_olsun_diye_benzersiz():
    assert TOKEN_KOLONU.unique is True


def test_yeni_referans_istegi_bekliyor_durumunda_baslar():
    assert DURUM_KOLONU.default.arg == DURUM_BEKLIYOR
