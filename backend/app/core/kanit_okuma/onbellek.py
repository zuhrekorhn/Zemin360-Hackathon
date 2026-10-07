"""Süreç içi, süreli önbellek (docs/dogrulama.md § 5.1 `onbellek.py`).

Bugün yalnızca sayfa ekran görüntülerinin model okunuşu için kullanılıyor: aynı
adres her değerlendirmede yeniden okutulmasın (maliyet) ve betim her seferinde
farklı yazılıp kalemin özetini boş yere değiştirmesin. Bellekte durur, süreç
yeniden başlayınca boşalır; tek süreçli kurulum için yeterli.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Generic, TypeVar

D = TypeVar("D")

GUN_SANIYE = 24 * 60 * 60


class ZamanliOnbellek(Generic[D]):
    def __init__(
        self,
        sure_sn: float = GUN_SANIYE,
        kapasite: int = 500,
        saat: Callable[[], float] = time.monotonic,
    ) -> None:
        self._sure = sure_sn
        self._kapasite = kapasite
        self._saat = saat
        self._kayitlar: OrderedDict[str, tuple[float, D]] = OrderedDict()

    def al(self, anahtar: str) -> D | None:
        kayit = self._kayitlar.get(anahtar)
        if kayit is None:
            return None
        zaman, deger = kayit
        if self._saat() - zaman > self._sure:
            del self._kayitlar[anahtar]
            return None
        return deger

    def koy(self, anahtar: str, deger: D) -> None:
        self._kayitlar[anahtar] = (self._saat(), deger)
        self._kayitlar.move_to_end(anahtar)
        while len(self._kayitlar) > self._kapasite:
            self._kayitlar.popitem(last=False)

    def temizle(self) -> None:
        self._kayitlar.clear()
