"""Dosyanın kaynak seviyesi: dosyanın kendisi değil, içindeki doğrulanabilir çapa kanıttır
(plan § 4.1, § 4.2). Saf kural.

Çapa doğrulayıcıları (`core/capalar/`) her çapa için bir kayıt yazar
(`kanit_parcasi.belge["capalar"]`): `{"tur": "qr", "sonuc": "dogrulandi", ...}`.
Seviye okuma anında bu kayıtlardan hesaplanır; kural değişirse eski dosyalar da
yeni kuralla okunur.

| sonuc          | anlamı                                                   | seviye |
|----------------|----------------------------------------------------------|--------|
| `dogrulandi`   | Düzenleyen doğruladı ve kimlik koşulu sağlandı           | A      |
| `kamuya_acik`  | Doğrulama adresi açıldı ama düzenleyen ya da ad koşulu yok | C    |
| `incelemede`   | GİRVAK elle doğrulayacak (e-Devlet barkodu)              | D      |
| `gecersiz`     | İmza bozuk / adres belgeyi doğrulamıyor                  | D      |
| (çapa yok)     | Çapasız yükleme                                          | D      |
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.kanit_okuma.belge import KaynakSeviyesi

DOGRULANDI = "dogrulandi"
KAMUYA_ACIK = "kamuya_acik"
INCELEMEDE = "incelemede"
GECERSIZ = "gecersiz"

_SEVIYE = {DOGRULANDI: KaynakSeviyesi.DUZENLEYEN, KAMUYA_ACIK: KaynakSeviyesi.KAMUYA_ACIK}
_SIRA = [KaynakSeviyesi.DUZENLEYEN, KaynakSeviyesi.KAMUYA_ACIK]


def dosya_seviyesi(belge: Mapping[str, Any]) -> KaynakSeviyesi:
    """En güçlü çapanın seviyesi; çapa yoksa beyan (D)."""
    seviyeler = {
        _SEVIYE[c.get("sonuc")] for c in belge.get("capalar", ()) if c.get("sonuc") in _SEVIYE
    }
    return next((s for s in _SIRA if s in seviyeler), KaynakSeviyesi.BEYAN)
