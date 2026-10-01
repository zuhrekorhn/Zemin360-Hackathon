"""Ad ve kimlik bütünlüğü kuralları (docs/plans/dogrulama-iyilestirme.md § 6.3, bulgu 48).

Saf: veritabanı ve ağ yok. Üç soru:
  - Ad kilitli mi? E-posta doğrulanınca kilitlenir; kilit ayrıca saklanmaz.
  - Bir metinde gencin adı geçiyor mu? Türkçe karakterden ve sıradan bağımsız,
    bütün ad parçaları ayrı kelime olarak geçmeli.
  - Ada dayalı kaynak en çok hangi seviyeye çıkar? Üç koşul birlikteyse A,
    biri eksikse en çok C (ad değiştirilerek sahiplik taklidi kapanır).
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata

from app.core.kanit_okuma.belge import KaynakSeviyesi
from app.core.metin import turkce_kucult

_KELIME = re.compile(r"[a-z0-9]+")


def ad_kilitli(eposta_dogrulandi_tarihi: dt.datetime | None) -> bool:
    return eposta_dogrulandi_tarihi is not None


def ad_parcalari(metin: str) -> list[str]:
    """Küçültülmüş, aksanı atılmış (ç→c, ı→i, ö→o…) kelimeler."""
    kucuk = turkce_kucult(metin).replace("ı", "i")
    sade = "".join(h for h in unicodedata.normalize("NFKD", kucuk) if not unicodedata.combining(h))
    return _KELIME.findall(sade)


def ad_eslesir(ad: str | None, metin: str | None) -> bool:
    """Adın bütün parçaları metinde ayrı kelime olarak geçiyor mu (sıra fark etmez)?"""
    parcalar = ad_parcalari(ad or "")
    if not parcalar:
        return False
    kelimeler = set(ad_parcalari(metin or ""))
    return all(p in kelimeler for p in parcalar)


def ada_dayali_seviye(
    *, ad_eslesti: bool, eposta_dogrulandi: bool, ad_kilitli_mi: bool
) -> KaynakSeviyesi:
    """Düzenleyenin sayfasında adla bulunan kanıtın tavanı: üç koşul → A, yoksa C."""
    if ad_eslesti and eposta_dogrulandi and ad_kilitli_mi:
        return KaynakSeviyesi.DUZENLEYEN
    return KaynakSeviyesi.KAMUYA_ACIK
