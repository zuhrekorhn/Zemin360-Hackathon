"""Kullanıcı metni dil denetimi (app/core/kullanici_dili.py › metin_ihlalleri)."""

import pytest

from app.core.kullanici_dili import metin_ihlalleri


@pytest.mark.parametrize(
    "metin",
    [
        "Arayüzü tek başına yaptığını açıkça yazmışsın.",
        "Denizde yalnız kalan tekneyle ilgili bir çalışma.",  # deniz, yalnız: hitap değil
        "Reklam ajansında çalıştın; bu ajansın müşterileri belli.",  # ajans: yasak terim değil
    ],
)
def test_temiz_metin(metin):
    assert metin_ihlalleri(metin) == []


@pytest.mark.parametrize(
    ("metin", "beklenen"),
    [
        ("Rolünüzü tek başınıza üstlendiğinizi yazdınız.", "hitap"),
        ("Size önerimiz şu.", "hitap"),
        ("Güven skoru yükseldi.", "terim: skor"),
        ("Rubriğe göre puanlandı.", "terim: rubrik"),
        ("Doğrulama Ajanı inceledi.", "terim: ajan"),
        ("Bu iş kalemi güçlü.", "terim: iş kalemi"),
        ("Kanıt açılıyor — ama ilgisiz.", "uzun tire"),
    ],
)
def test_ihlaller_yakalanir(metin, beklenen):
    assert any(i.startswith(beklenen) for i in metin_ihlalleri(metin))


def test_firmaya_siz_hitabi_serbest():
    assert metin_ihlalleri("Kartı inceleyebilirsiniz.", hitap="siz") == []
