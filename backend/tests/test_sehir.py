"""Şehir adlarının Türkçe'ye duyarlı karşılaştırılması.

Eşleştirme'nin tek sert metin filtresi bu; yazım farkı adayı skor
hesaplanmadan eliyor. Testler gerçek veritabanında görülen vakayı
(`'istanbul'` ile `'İstanbul'`) sabitliyor.
"""

from app.core.sehir import (
    SEHIRLER,
    sehir_anahtari,
    sehir_kanonik,
    sehirler_esit_mi,
    turkce_kucult,
)


def test_81_il_var():
    assert len(SEHIRLER) == 81
    assert len(set(SEHIRLER)) == 81


def test_noktali_buyuk_i_dogru_kuculuyor():
    """Python'ın kendi lower()'ı burada i + U+0307 üretiyor, eşleşme bozuluyor."""
    assert turkce_kucult("İstanbul") == "istanbul"
    assert "İstanbul".lower() != "istanbul"  # neden elle yazdığımızın kanıtı


def test_noktasiz_buyuk_i_dogru_kuculuyor():
    assert turkce_kucult("IĞDIR") == "ığdır"


def test_kucuk_harf_farki_eslesmeyi_bozmuyor():
    """Gerçek veride görülen vaka: kullanıcı 'istanbul' yazmıştı."""
    assert sehirler_esit_mi("istanbul", "İstanbul")
    assert sehirler_esit_mi("  İSTANBUL ", "istanbul")


def test_farkli_sehirler_esit_sayilmaz():
    assert not sehirler_esit_mi("İzmir", "İstanbul")
    # Karşılaştırma katmanı katı: Türkçe'de "ıstanbul" başka bir dize.
    # (Yazma anında hoşgörü var, bkz. test_turkce_klavyesiz_yazim_da_anlasiliyor)
    assert not sehirler_esit_mi("ıstanbul", "İstanbul")


def test_kanonik_yazim_listeden_geliyor():
    assert sehir_kanonik("istanbul") == "İstanbul"
    assert sehir_kanonik("İZMİR") == "İzmir"
    assert sehir_kanonik("  ankara  ") == "Ankara"


def test_turkce_klavyesiz_yazim_da_anlasiliyor():
    """ "IZMIR" Türkçe kurallarına göre "ızmır"; ama kastedilen belli."""
    assert sehir_kanonik("IZMIR") == "İzmir"
    assert sehir_kanonik("Izmir") == "İzmir"
    assert sehir_kanonik("Mugla") == "Muğla"
    assert sehir_kanonik("ıstanbul") == "İstanbul"


def test_listede_olmayan_yer_silinmiyor():
    """İlçe ya da yurt dışı olabilir; bilmediğimizi atmak yazım hatasından kötü."""
    assert sehir_kanonik("Ayvalık") == "Ayvalık"


def test_bos_deger_none_olur():
    assert sehir_kanonik(None) is None
    assert sehir_kanonik("   ") is None


def test_uzaktan_bir_sehir_degil():
    """Konum ve çalışma modeli ayrı alanlar (bkz. app/core/calisma_modeli.py)."""
    assert sehir_kanonik("uzaktan") == "uzaktan"  # il listesinde yok, metin olarak kalır
    assert "uzaktan" not in [sehir_anahtari(s) for s in SEHIRLER]


def test_anahtar_bosluklari_sadelestirir():
    assert sehir_anahtari("  Afyonkarahisar  ") == "afyonkarahisar"
