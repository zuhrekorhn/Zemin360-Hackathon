"""Uzun kanıt metni: kesme yok, seçme var (plan § 5.4).

8.000 karakteri aşmayan metin olduğu gibi kullanılır. Aşan metin ~1.500
karakterlik, 200 karakter örtüşen parçalara bölünür; her iddia (iş, sonuç, pay)
için en ilgili 4 parça ve her zaman ilk parça (başlık, README girişi) seçilir,
özgün sırasıyla birleştirilir. Model yalnızca bunları görür; alıntı denetimi tam
metne karşı yapılır (cekirdek.py).

Embedding dışarıdan verilir (`Gomucu`): uygulama Voyage'ı, değerlendirme seti
kayıtlı yanıtı kullanır. Embedding hata verirse metnin başı kullanılır: hiçbir
dış servis hatası değerlendirmeyi düşürmez (İ9).
"""

from __future__ import annotations

import logging
import math
from collections.abc import Awaitable, Callable, Sequence

logger = logging.getLogger("zemin360.dogrulama")

KISA_METIN = 8_000
PARCA_BOYU = 1_500
ORTUSME = 200
IDDIA_BASINA = 4
AYRAC = "\n[…]\n"

Gomucu = Callable[[list[str], str], Awaitable[list[list[float]]]]


def bol(metin: str) -> list[str]:
    adim = PARCA_BOYU - ORTUSME
    return [metin[i : i + PARCA_BOYU] for i in range(0, max(len(metin) - ORTUSME, 1), adim)]


def _kosinus(a: Sequence[float], b: Sequence[float]) -> float:
    pay = sum(x * y for x, y in zip(a, b, strict=False))
    payda = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return pay / payda if payda else 0.0


async def sec(metin: str, sorgular: Sequence[str], gom: Gomucu) -> str:
    if len(metin) <= KISA_METIN:
        return metin
    parcalar = bol(metin)
    sorgular = [s for s in sorgular if s and s.strip()]
    if not sorgular:
        return metin[:KISA_METIN]
    try:
        parca_vektorleri = await gom(parcalar, "document")
        sorgu_vektorleri = await gom(list(sorgular), "query")
    except Exception:
        logger.warning("Parça seçimi için embedding alınamadı; metnin başı kullanıldı")
        return metin[:KISA_METIN]

    secilen = {0}
    for sorgu in sorgu_vektorleri:
        sirali = sorted(
            range(len(parcalar)), key=lambda i: _kosinus(sorgu, parca_vektorleri[i]), reverse=True
        )
        secilen.update(sirali[:IDDIA_BASINA])
    return AYRAC.join(parcalar[i] for i in sorted(secilen))
