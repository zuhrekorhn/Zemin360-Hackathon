"""Uygulama içi bildirim yazma ve sayma.

Bildirimi olayın kendisi yazar (eşleşme geçişi, pipeline, referans yanıtı, takip,
canlılık), aynı işlemde: olay olup bildirim kaybolmasın, bildirim olup olay geri
alınmasın. Okuma uçları `app/api/bildirimler.py`'de; okunmamış sayısı `GET /me`'de.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bildirim import Bildirim


def bildirim_ekle(
    oturum: AsyncSession,
    hesap_id: uuid.UUID | None,
    tur: str,
    metin: str,
    eslesme_id: uuid.UUID | None = None,
) -> None:
    """Bildirimi oturuma ekler; commit çağıranın işi (olayla aynı işlem).

    Hesabı olmayan profil için sessizce atlanır: okuyacak kimse yok.
    """
    if hesap_id is None:
        return
    oturum.add(Bildirim(hesap_id=hesap_id, tur=tur, metin=metin, eslesme_id=eslesme_id))


async def okunmamis_sayisi(oturum: AsyncSession, hesap_id: uuid.UUID) -> int:
    return await oturum.scalar(
        select(func.count())
        .select_from(Bildirim)
        .where(Bildirim.hesap_id == hesap_id, Bildirim.okundu_tarihi.is_(None))
    )


async def yakinda_yazildi_mi(
    oturum: AsyncSession,
    hesap_id: uuid.UUID | None,
    tur: str,
    eslesme_id: uuid.UUID,
    saat: int = 24,
) -> bool:
    """Aynı eşleşme için aynı türde bildirim son `saat` içinde yazıldı mı?

    "İlgi göster → geri çek → yeniden göster" döngüsü karşı tarafa her seferinde yeni
    bildirim yağdırmasın diye: olay (geçiş) yine uygulanır, yalnızca bildirim tekrarlanmaz.
    """
    if hesap_id is None:
        return False
    sinir = dt.datetime.now(dt.UTC) - dt.timedelta(hours=saat)
    return bool(
        await oturum.scalar(
            select(func.count())
            .select_from(Bildirim)
            .where(
                Bildirim.hesap_id == hesap_id,
                Bildirim.tur == tur,
                Bildirim.eslesme_id == eslesme_id,
                Bildirim.olusturma_tarihi > sinir,
            )
        )
    )
