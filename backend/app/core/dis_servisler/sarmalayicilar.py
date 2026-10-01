"""Her dış servis çağrısına aynı biçimde uygulanan sarmalayıcılar (Decorator, plan § 14.3).

    @gozlemli("eposta")
    @zaman_asimli(10)
    async def gonder(...): ...

Sıra önemli: `gozlemli` dışta durur ki zaman aşımı da hata olarak sayılsın.
İkisi de hatayı yutmaz; zarif düşüş (İ9) çağıranın kararıdır, çünkü "—"
yazmak mı, log'a düşüp devam etmek mi, ona çağıran karar verir.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

from app.core.dis_servisler.saglik import SAGLIK

logger = logging.getLogger("zemin360.dis_servisler")

P = ParamSpec("P")
T = TypeVar("T")


def zaman_asimli(
    saniye: float | Callable[[], float],
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Çağrı `saniye` içinde bitmezse `TimeoutError`.

    Süre ayardan okunuyorsa bir fonksiyon verilir: değer çağrı anında okunur,
    modül yüklenirken değil.
    """

    def sar(fonk: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(fonk)
        async def sarili(*args: P.args, **kwargs: P.kwargs) -> T:
            sure = saniye() if callable(saniye) else saniye
            return await asyncio.wait_for(fonk(*args, **kwargs), timeout=sure)

        return sarili

    return sar


def gozlemli(servis: str) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Süreyi ve sonucu log'a, başarı ya da hatayı sağlık kaydına yazar."""

    def sar(fonk: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(fonk)
        async def sarili(*args: P.args, **kwargs: P.kwargs) -> T:
            baslangic = time.perf_counter()
            try:
                sonuc = await fonk(*args, **kwargs)
            except Exception as hata:
                SAGLIK.hata(servis, hata)
                logger.warning(
                    "dis_servis servis=%s sonuc=hata tur=%s sure_ms=%d",
                    servis,
                    type(hata).__name__,
                    (time.perf_counter() - baslangic) * 1000,
                )
                raise
            SAGLIK.basari(servis)
            logger.info(
                "dis_servis servis=%s sonuc=basari sure_ms=%d",
                servis,
                (time.perf_counter() - baslangic) * 1000,
            )
            return sonuc

        return sarili

    return sar
