"""İlan (ihtiyaç kartı) kapatma nedenleri (docs/plans/firma-akisi.md § 0 karar 7, § 7).

Neden yalnızca GİRVAK'a görünür (program başarısı sayılır); karşı taraf
yalnızca "fırsat kapandı" görür. Kapanan ilan tekrar açılmaz.
"""

from __future__ import annotations

from typing import Literal

PLATFORMDA_BULUNDU = "platformda_bulundu"
BASKA_YOLDAN_BULUNDU = "baska_yoldan_bulundu"
VAZGECILDI = "vazgecildi"

KAPANMA_NEDENLERI: tuple[str, ...] = (PLATFORMDA_BULUNDU, BASKA_YOLDAN_BULUNDU, VAZGECILDI)
KapanmaNedeni = Literal["platformda_bulundu", "baska_yoldan_bulundu", "vazgecildi"]
