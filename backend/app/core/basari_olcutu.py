"""İhtiyaç kartındaki başarı kriterinin yapılandırılmış hâli (saf kurallar).

Model çıkarır, kural karar verir: sohbet modeli başarı kriterinden metriği,
bugünkü değeri, hedef değeri ve süreyi ayrı alanlar olarak çıkarır; "ölçülebilir
mi" kararı metne bakan bir düzenli ifadeyle değil, hedef değerin varlığıyla
verilir. Türkçede "yarıya insin", "iki kat", "bir haftaya düşsün" sayı içermez
ama ölçülebilir; "2024'te memnuniyet" sayı içerir ama ölçülebilir değil.

Hedef yoksa sohbet bir kez sorar. Firma ölçmediğini ya da bilmediğini söylerse
(`olcum_bilinmiyor`) sorulmaz; kart "ölçüm yöntemi belirlenecek" işaretiyle
kaydedilir. İşaret saklanmaz, hedefin yokluğundan okunur.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

METIN_ALANLARI = ("metrik", "mevcut_deger", "hedef_deger", "sure")
OLCUM_BILINMIYOR = "olcum_bilinmiyor"


def hedef_var_mi(olcut: Mapping[str, Any] | None) -> bool:
    return bool(olcut and olcut.get("hedef_deger"))


def olcum_belirlenecek(olcut: Mapping[str, Any] | None) -> bool:
    """Kartta "ölçüm yöntemi belirlenecek" işareti.

    Ölçütü hiç olmayan kart (bu alandan önce kaydedilmiş) işaretlenmez.
    """
    return olcut is not None and not hedef_var_mi(olcut)


def hedef_sorulmali(taslak: Mapping[str, Any]) -> bool:
    """Başarı kriteri var ama hedef yok ve firma bilmediğini söylemedi."""
    olcut = taslak.get("basari_olcutu") or {}
    return (
        bool(taslak.get("basari_kriteri"))
        and not hedef_var_mi(olcut)
        and not olcut.get(OLCUM_BILINMIYOR)
    )
