"""İlan (ihtiyaç kartı) düzenleme kuralları (docs/plans/ilan-duzenleme.md).

Saf fonksiyonlar: veritabanı yok. Uç (app/api/ihtiyac_kartlari.py) kuralı sorar,
sonucu uygular. Tablo tests/test_ihtiyac_duzenleme.py'de sabit.

İlan yerinde düzenlenir: eşleştirme aynı ilan için yeniden çalışır, firmanın
karar verdiği kayıtlar ve gencin ilgisi kendiliğinden korunur. Eski metne göre
yazılmış "Neden uygun?" kalmasın diye yeniden yazılabilecek gerekçeler sıfırlanır.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from app.agents.eslesme_durumu import IHTIYAC_ACIK
from app.agents.eslestirme import (
    DURUM_GENC_ILGILENDI,
    DURUM_ILGILENILIYOR,
    DURUM_KABUL_EDILDI,
    DURUM_ONERILDI,
)

ILAN_KAPALI = "Bu ihtiyaç kapandı; düzenlenemez."
ISBIRLIGI_BASLADI = "Bu ihtiyaçla bir iş birliği başladı; düzenlenemez."

# İlanın düzenlenebilir alanları. `aranan` (kapı) burada yok: değiştirilemez.
IHTIYAC_ALANLARI: tuple[str, ...] = (
    "problem_tanimi",
    "basari_kriteri",
    "basari_olcutu",
    "kisitlar",
    "sehir_tercihi",
    "calisma_modeli",
    "musaitlik_tercihi",
    "aranan_firma_turleri",
    "isbirligi_turu",
)

# Gerekçesi yeniden yazılacaklar: pipeline'ın gerekçe ürettiği ve firmanın henüz
# kesin karar vermediği kayıtlar. `genc_ilgilendi` karar 14 gereği dokunulmaz.
_GEREKCESI_SIFIRLANANLAR = frozenset({DURUM_ONERILDI, DURUM_ILGILENILIYOR})

# Aday tarafı bu ilanla ilgilenmiş, ayrıntının değiştiğini bilmeli.
_BILDIRIM_ALANLAR = frozenset({DURUM_ILGILENILIYOR, DURUM_GENC_ILGILENDI})


def duzenlenebilir_mi(ilan_durumu: str, eslesme_durumlari: Iterable[str]) -> str | None:
    """Düzenlenemiyorsa kullanıcıya gösterilecek sebep (409), düzenlenebiliyorsa None."""
    if ilan_durumu != IHTIYAC_ACIK:
        return ILAN_KAPALI
    if any(durum == DURUM_KABUL_EDILDI for durum in eslesme_durumlari):
        return ISBIRLIGI_BASLADI
    return None


def _normal(deger: Any) -> Any:
    """Karşılaştırma için: boş metin None, liste ve demet liste."""
    if isinstance(deger, str):
        return deger.strip() or None
    if isinstance(deger, list | tuple):
        return [_normal(d) for d in deger]
    if isinstance(deger, Mapping):
        return {k: _normal(v) for k, v in deger.items()}
    return deger


def degisen_alanlar(eski: Mapping[str, Any], yeni: Mapping[str, Any]) -> set[str]:
    """`yeni`'deki alanlardan gerçekten değişenler (gönderilmeyen alan değişmemiştir)."""
    return {alan for alan, deger in yeni.items() if _normal(deger) != _normal(eski.get(alan))}


def gerekcesi_sifirlanacak(durum: str) -> bool:
    return durum in _GEREKCESI_SIFIRLANANLAR


def bildirim_alacak(durum: str) -> bool:
    return durum in _BILDIRIM_ALANLAR
