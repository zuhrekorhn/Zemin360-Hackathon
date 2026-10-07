"""Kart düzenleme kuralları (docs/agent-specs.md § 1-6.3).

Saf fonksiyonlar: veritabanı yok. Uçlar ve servis (app/servisler/kart_duzenleme.py)
kuralı sorar, sonucu uygular. Tablo tests/test_kart_duzenleme.py'de sabit.

Temel ilke: önce gerçek kanıtla puan alıp sonra metni şişirmenin önüne geçmek.
Doğrulanmış bir iş kaleminin içeriği ya da linki değişirse o kalemin güven
göstergesi sıfırlanır ve yeniden değerlendirilir; değişmeyen kalemlerinki korunur.
Değişiklikten önce verilmiş referans yanıtları silinmez, geçmiş olarak kalır
ama puana girmez.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

# Kartın düzenlenebilir alanları.
KART_ALANLARI: tuple[str, ...] = (
    "rol_alani",
    "deneyim_seviyesi",
    "sektor_ilgi_alani",
    "araclar_teknolojiler",
    "sertifikalar",
    "diller",
)

# İş kaleminin (iddianın) düzenlenebilir alanları. Kanıt burada değil:
# parçalar Doğrulama'nın tek kapısından eklenir ve kaldırılır
# (app/servisler/dogrulama/parcalar.py).
IS_KALEMI_ALANLARI: tuple[str, ...] = (
    "baslik",
    "aciklama",
    "olculebilir_sonuc",
    "kendi_rolu",
    "is_turu",
)

# Değişince güven göstergesini sıfırlayan ve referans yanıtlarını geçmişe atanlar:
# iddianın kendisi. İş türü (proje, staj…) bir etiket; iddiayı değiştirmez. Kanıt
# değişikliği de iddiayı değiştirmez: gösterge yeniden değerlendirilir ama referans
# yanıtları geçerli kalır (docs/dogrulama.md § 2: kanıt eklemek puanı hiçbir zaman düşürmez).
DOGRULAMAYI_SIFIRLAYANLAR = frozenset({"baslik", "aciklama", "olculebilir_sonuc", "kendi_rolu"})

# Değişince yeniden eşleştirme gerektiren profil alanları: sert filtreler.
FILTRE_ALANLARI = frozenset({"sehir", "calisma_modelleri", "musaitlikler"})


def _normal(deger: Any) -> Any:
    """Karşılaştırma için: boş metin None, liste liste."""
    if isinstance(deger, str):
        return deger.strip() or None
    if isinstance(deger, list | tuple):
        return list(deger)
    return deger


def degisen_alanlar(eski: Mapping[str, Any], yeni: Mapping[str, Any]) -> set[str]:
    """`yeni`'deki alanlardan gerçekten değişenler (gönderilmeyen alan değişmemiştir)."""
    return {alan for alan, deger in yeni.items() if _normal(deger) != _normal(eski.get(alan))}


def versiyon_artmali_mi(degisenler: Iterable[str]) -> bool:
    """Aynı değerle gelen düzenleme sürümü artırmaz, hazırlamayı tetiklemez."""
    return any(True for _ in degisenler)


def dogrulama_sifirlanmali_mi(degisenler: Iterable[str]) -> bool:
    return any(alan in DOGRULAMAYI_SIFIRLAYANLAR for alan in degisenler)


def yeniden_eslestirme_gerekir_mi(degisen_profil_alanlari: Iterable[str]) -> bool:
    """Profilde filtre alanı değiştiyse kartlar yeniden eşleşir (doğrulama gerekmez)."""
    return any(alan in FILTRE_ALANLARI for alan in degisen_profil_alanlari)
