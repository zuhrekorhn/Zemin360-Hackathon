"""GİRVAK inceleme işaretinin durumu (docs/dogrulama.md § 9).

Eşleşme, takip ve referans durum makineleriyle aynı desen: geçiş kuralı tek
yerde ve saf; servis yalnızca söyleneni uygular.

    acik ──kapandi────────▶ kapandi         ("sorun yok"; talepte "onaylandı")
      └────dogrulanamadi──▶ dogrulanamadi   (talepte "reddedildi")

Aynı kararın tekrarı yan etkisizdir (`None`). Kapanmış işarette başka karar
409: kararın yan etkisi (ör. ad değişikliği) geri alınmaz; GİRVAK yeni
bir işaretle yeniden bakar.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from typing import Protocol

ACIK = "acik"
KAPANDI = "kapandi"
DOGRULANAMADI = "dogrulanamadi"
DURUMLAR = (ACIK, KAPANDI, DOGRULANAMADI)
KARARLAR = (KAPANDI, DOGRULANAMADI)


class GecersizKarar(Exception):
    """Kapanmış işarete farklı karar. Mesaj GİRVAK'a gösterilir (uçta 409)."""


def inceleme_gecisi(durum: str, karar: str) -> str | None:
    """Kararın götürdüğü durum; aynı kararın tekrarıysa `None` (yan etkisiz)."""
    if karar not in KARARLAR:
        raise ValueError(f"Geçersiz karar: {karar}")
    if durum == ACIK:
        return karar
    if durum == karar:
        return None
    raise GecersizKarar("Bu işaret başka bir kararla kapandı; karar değiştirilemez.")


class _Karar(Protocol):
    tur: str
    durum: str
    kapanma_tarihi: dt.datetime | None


def gecerli_dogrulanamadilar(isaretler: Iterable[_Karar]) -> list[_Karar]:
    """Kalemin "Doğrulanamadı" etiketi (docs/dogrulama.md § 9): türünün SON kararı "doğrulanamadı"
    olan işaretler. Açık işaret etiketi kaldırmaz (karar inceleme bitene dek
    geçerli); gencin itirazı aynı türden yeni bir işaret açar, GİRVAK onu "sorun
    yok" diye kapatırsa etiket kalkar. Puan değişmez (İ1)."""
    son: dict[str, _Karar] = {}
    for isaret in isaretler:
        if isaret.durum == ACIK or isaret.kapanma_tarihi is None:
            continue
        onceki = son.get(isaret.tur)
        if onceki is None or isaret.kapanma_tarihi > onceki.kapanma_tarihi:
            son[isaret.tur] = isaret
    return [i for i in son.values() if i.durum == DOGRULANAMADI]
