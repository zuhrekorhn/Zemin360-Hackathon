"""Vakaları bir değerlendiriciden geçirir.

Bir vakanın hatası diğerlerini durdurmaz: istisna sonucun `hata` alanına
yazılır ve karnede "sonuç üretemedi" olarak görünür.
"""

from __future__ import annotations

import asyncio

from degerlendirme.degerlendirici import Degerlendirici, Degerlendirme
from degerlendirme.kaset import KasetEksik
from degerlendirme.olcutler import VakaSonucu
from degerlendirme.vaka import Vaka


async def _tek(degerlendirici: Degerlendirici, vaka: Vaka) -> VakaSonucu:
    try:
        sonuc = await degerlendirici.degerlendir(vaka)
    except KasetEksik as hata:
        sonuc = Degerlendirme(hata="kaset_eksik", ayrinti={"neden": str(hata)})
    except Exception as hata:  # karne, tek vakanın istisnasıyla durmamalı
        sonuc = Degerlendirme(hata=type(hata).__name__, ayrinti={"neden": str(hata)})
    return VakaSonucu(vaka=vaka, degerlendirme=sonuc)


async def hepsini_degerlendir(
    degerlendirici: Degerlendirici, vakalar: list[Vaka], *, es_zamanli: int = 4
) -> list[VakaSonucu]:
    sinir = asyncio.Semaphore(es_zamanli)

    async def sinirli(vaka: Vaka) -> VakaSonucu:
        async with sinir:
            return await _tek(degerlendirici, vaka)

    return list(await asyncio.gather(*(sinirli(v) for v in vakalar)))
