"""Dış servisin aylık tavanı (plan § 14.4): çağrıdan önce hak alınır.

Artırma ve tavan denetimi tek sorguda (`INSERT … ON CONFLICT DO UPDATE … WHERE
sayi < tavan RETURNING`): eşzamanlı iki yükleme tavanı birlikte aşamaz. Hak,
çağıranın işlemiyle birlikte yazılır; işlem geri alınırsa hak da geri gelir
(o çağrı sayılmamış olur: tavan maliyet için kaba bir sınırdır).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.servis_kullanimi import ServisKullanimi


def donem(an: dt.datetime | None = None) -> str:
    return (an or dt.datetime.now(dt.UTC)).strftime("%Y-%m")


async def hak_al(oturum: AsyncSession, servis: str, aylik_tavan: int) -> bool:
    """Bu ayın tavanı dolmadıysa sayacı bir artırır ve True döner."""
    if aylik_tavan <= 0:
        return False
    sorgu = insert(ServisKullanimi).values(servis=servis, donem=donem(), sayi=1)
    sorgu = sorgu.on_conflict_do_update(
        index_elements=[ServisKullanimi.servis, ServisKullanimi.donem],
        set_={"sayi": ServisKullanimi.sayi + 1},
        where=ServisKullanimi.sayi < aylik_tavan,
    ).returning(ServisKullanimi.sayi)
    return await oturum.scalar(sorgu) is not None
