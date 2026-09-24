"""Doğrulama Ajanı'nın hesap mantığı — LLM ve ağ olmadan.

Sınırlar docs/agent-specs.md § 4 ve docs/sequence-diagrams.md § Akış 2'den.
"""

import datetime as dt

import pytest
from pydantic import ValidationError

from app.agents.dogrulama import (
    DURUM_BEKLIYOR,
    DURUM_ONAYLANDI,
    DURUM_YANIT_YOK,
    REFERANS_TIMEOUT_GUN,
    RubrikPuani,
    link_ozetini_cikar,
    referans_puanina_cevir,
    zaman_asimina_ugradi_mi,
)
from app.models.referans_istegi import ReferansIstegi


def test_rubrik_bilesenleri_0_3_araliginda_olmali():
    with pytest.raises(ValidationError):
        RubrikPuani(kanit_orijinalligi=4, sonuc_olculebilirligi=1, rol_netligi=1, gerekce_metni="x")
    with pytest.raises(ValidationError):
        RubrikPuani(
            kanit_orijinalligi=-1, sonuc_olculebilirligi=1, rol_netligi=1, gerekce_metni="x"
        )


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


def test_sure_dolmadan_zaman_asimi_yok():
    yeni = dt.datetime.now(dt.UTC) - dt.timedelta(days=REFERANS_TIMEOUT_GUN - 1)
    assert zaman_asimina_ugradi_mi(yeni, DURUM_BEKLIYOR) is False


def test_sure_dolunca_zaman_asimi():
    eski = dt.datetime.now(dt.UTC) - dt.timedelta(days=REFERANS_TIMEOUT_GUN, hours=1)
    assert zaman_asimina_ugradi_mi(eski, DURUM_BEKLIYOR) is True


def test_yanitlanmis_referans_zaman_asimina_ugramaz():
    """Referans cevapladıysa süre dolsa bile durumu değişmemeli."""
    eski = dt.datetime.now(dt.UTC) - dt.timedelta(days=90)
    assert zaman_asimina_ugradi_mi(eski, DURUM_ONAYLANDI) is False
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


def test_link_ozeti_baslik_ve_metayi_alir():
    html = (
        "<html><head><title> Kütüphane  Takip </title>"
        '<meta name="description" content="400 kitap takibi">'
        "</head><body>çok uzun içerik</body></html>"
    )
    assert link_ozetini_cikar(html) == "Kütüphane Takip — 400 kitap takibi"


def test_bos_sayfa_ozeti_bos_dizge_dondurmez():
    assert "okunamadı" in link_ozetini_cikar("<html><body>x</body></html>")
