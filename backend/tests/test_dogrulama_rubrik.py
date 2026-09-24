"""Doğrulama Ajanı'nın hesap mantığı — LLM ve ağ olmadan.

Sınırlar docs/agent-specs.md § 4 ve docs/sequence-diagrams.md § Akış 2'den.
"""

import datetime as dt

import pytest
from pydantic import ValidationError

from app.agents.dogrulama import (
    DURUM_BEKLIYOR,
    DURUM_YANIT_YOK,
    DURUM_YANITLANDI,
    REFERANS_TIMEOUT_GUN,
    RubrikPuani,
    link_ozetini_cikar,
    linki_normalize_et,
    referans_puanina_cevir,
    ucuncu_taraf_onayi_hesapla,
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


def test_yanitlamis_referans_yoksa_sifir():
    assert ucuncu_taraf_onayi_hesapla([]) == 0


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


def test_semasiz_linke_https_eklenir():
    """Kullanıcı sohbette linki çoğu zaman şemasız yazıyor."""
    assert linki_normalize_et("github.com/ornek/kutuphane") == "https://github.com/ornek/kutuphane"


def test_mevcut_sema_korunur():
    assert linki_normalize_et("http://ornek.com") == "http://ornek.com"
    assert linki_normalize_et("https://ornek.com") == "https://ornek.com"


def test_bosluklar_ve_bastaki_egik_cizgi_temizlenir():
    assert linki_normalize_et("  //ornek.com/yol  ") == "https://ornek.com/yol"


def test_link_ozeti_baslik_ve_metayi_alir():
    html = (
        "<html><head><title> Kütüphane  Takip </title>"
        '<meta name="description" content="400 kitap takibi">'
        "</head><body>çok uzun içerik</body></html>"
    )
    assert link_ozetini_cikar(html) == "Kütüphane Takip — 400 kitap takibi"


def test_uzun_head_icindeki_title_okunur():
    """GitHub gibi siteler <title>'ı sayfanın epey içine koyuyor."""
    html = "<html><head>" + '<link rel="x">' * 3000 + "<title>pgvector</title></head>"
    assert link_ozetini_cikar(html) == "pgvector"


def test_open_graph_etiketleri_okunur():
    """og:* etiketleri name= değil property= kullanıyor."""
    html = (
        '<html><head><meta property="og:title" content="pgvector/pgvector">'
        '<meta property="og:description" content="Vector similarity search"></head>'
    )
    assert link_ozetini_cikar(html) == "pgvector/pgvector — Vector similarity search"


def test_content_once_yazilmis_meta_da_okunur():
    html = '<html><head><meta content="Ters sıra" property="og:title"></head>'
    assert link_ozetini_cikar(html) == "Ters sıra"


def test_title_varken_og_title_kullanilmaz():
    html = (
        "<html><head><title>Gerçek başlık</title>"
        '<meta property="og:title" content="Sosyal başlık"></head>'
    )
    assert link_ozetini_cikar(html).startswith("Gerçek başlık")


def test_bos_sayfa_ozeti_bos_dizge_dondurmez():
    assert "okunamadı" in link_ozetini_cikar("<html><body>x</body></html>")


# --- İtiraz notu ----------------------------------------------------------
# Not rubriğe giriyor ama "doğrulanmış bilgi" olarak değil; kuralların
# prompt'ta yazılı olduğunu burada sabitliyoruz (LLM'e gitmeden).

from app.agents.dogrulama import RUBRIK_SABLONU, RUBRIK_TALIMATI  # noqa: E402


def test_itiraz_notu_sablonda_yer_aliyor():
    """Daha önce forma yazılan açıklama hiçbir yere gitmiyordu."""
    assert "{itiraz_notu}" in str(RUBRIK_SABLONU)


def test_itiraz_notu_beyan_olarak_isaretleniyor():
    assert "DOĞRULANMIŞ BİLGİ DEĞİL" in RUBRIK_TALIMATI
    assert "beyan" in RUBRIK_TALIMATI


def test_itiraz_notu_tek_basina_tam_puan_vermiyor():
    assert "tam puana (3) tek başına yetmez" in RUBRIK_TALIMATI


def test_itiraz_notunun_tonu_olcut_degil():
    """'Ne kadar ısrarlı yazılmış' bir kriter olamaz (önyargı riski)."""
    assert "tonuna" in RUBRIK_TALIMATI
