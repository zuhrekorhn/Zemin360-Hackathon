"""Görselin algısal özeti (pHash; plan § 9, `ayni_iddia_cok_hesapta`).

SHA-256 yalnızca birebir aynı dosyayı yakalar; yeniden kaydedilmiş, küçültülmüş
ya da biçimi değişmiş görselin özeti başkadır. Algısal özet görünüşe bakar:
32×32 gri görüntünün iki boyutlu DCT'sinin düşük frekanslı 8×8 bloğu, ortancanın
üstü 1, altı 0 (imagehash'in `phash`'i ile aynı yöntem). Benzerlik bit farkıyla
(Hamming uzaklığı) ölçülür.

Saf Python: 32×32'lik dönüşüm için numpy / scipy bağımlılığına gerek yok.
Veritabanı ve ağ yok.
"""

from __future__ import annotations

import io
import logging
import math
from functools import lru_cache

logger = logging.getLogger("zemin360.gorsel_ozeti")

_BOYUT = 32
_BLOK = 8
# 64 bitten en çok bu kadar farklıysa "benzer görsel" (imagehash topluluğunun
# yaygın eşiği 5-10; işaret yalnızca incelemeye düşürdüğü için ortadan biraz sıkı).
BENZERLIK_ESIGI = 6


@lru_cache(maxsize=1)
def _kosinusler() -> tuple[tuple[float, ...], ...]:
    """DCT-II katsayıları: [k][n] = cos(π (2n + 1) k / 2N); yalnızca ilk 8 frekans."""
    return tuple(
        tuple(math.cos(math.pi * (2 * n + 1) * k / (2 * _BOYUT)) for n in range(_BOYUT))
        for k in range(_BLOK)
    )


def _dusuk_frekanslar(pikseller: list[list[float]]) -> list[float]:
    cos = _kosinusler()
    # Satırlar, sonra sütunlar (ayrılabilir dönüşüm); yalnızca 8×8 blok hesaplanır.
    satirlar = [[sum(c * p for c, p in zip(cos[k], satir, strict=True)) for k in range(_BLOK)]
                for satir in pikseller]  # fmt: skip
    return [
        sum(cos[u][n] * satirlar[n][v] for n in range(_BOYUT))
        for u in range(_BLOK)
        for v in range(_BLOK)
    ]


def algisal_ozet(veri: bytes) -> str | None:
    """16 onaltılık karakter (64 bit); görsel açılamazsa None (işaret yalnızca eksik kalır)."""
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(veri)) as gorsel:
            kucuk = gorsel.convert("L").resize((_BOYUT, _BOYUT), Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, OSError):
        logger.warning("algisal ozet hesaplanamadi", exc_info=True)
        return None
    degerler = list(kucuk.tobytes())  # "L" kipi: piksel başına bir bayt
    pikseller = [[float(d) for d in degerler[i * _BOYUT : (i + 1) * _BOYUT]] for i in range(_BOYUT)]
    blok = _dusuk_frekanslar(pikseller)
    sirali = sorted(blok)
    ortanca = (sirali[31] + sirali[32]) / 2
    bitler = 0
    for deger in blok:
        bitler = (bitler << 1) | (1 if deger > ortanca else 0)
    return f"{bitler:016x}"


def uzaklik(a: str, b: str) -> int:
    """İki algısal özet arasındaki farklı bit sayısı."""
    return (int(a, 16) ^ int(b, 16)).bit_count()


def benzer_mi(a: str | None, b: str | None) -> bool:
    return bool(a and b) and uzaklik(a, b) <= BENZERLIK_ESIGI
