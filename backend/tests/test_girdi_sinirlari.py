"""Şema düzeyinde girdi sınırları: kullanıcı metni başka kullanıcıya giden e-postaya,
modele ve firmaya gösterilen karta giriyor; uzunluk ve biçim sunucuda sınırlanır."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import KayitIstegi
from app.schemas.sohbet import CEVAP_EN_COK, SohbetCevapIstegi

OTURUM = "00000000-0000-0000-0000-000000000001"
FIRMA = {
    "tur": "kobi",
    "sektor": "gıda",
    "sehir": "İstanbul",
}


def _kayit(ad: str) -> KayitIstegi:
    return KayitIstegi(
        email="a@ornek.com",
        sifre="yeterince-uzun",
        rol="kurum",
        ad=ad,
        firma_profili=FIRMA,
        kvkk_onay=True,
    )


def test_sohbet_cevabi_ust_sinirini_asamaz():
    SohbetCevapIstegi(oturum_id=OTURUM, cevap="x" * CEVAP_EN_COK)
    with pytest.raises(ValidationError):
        SohbetCevapIstegi(oturum_id=OTURUM, cevap="x" * (CEVAP_EN_COK + 1))


def test_ad_kisa_ve_tek_satir():
    assert _kayit("  Elif Demir ").ad == "Elif Demir"
    oltalama = "Güvenlik uyarısı\nTıkla: http://kotu.example"
    for kotu in ["x" * 101, oltalama, "Ad\tSoyad", "   "]:
        with pytest.raises(ValidationError):
            _kayit(kotu)
