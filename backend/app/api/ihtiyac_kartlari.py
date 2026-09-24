"""İhtiyaç kartı okuma uç noktası.

Gizlilik: yanıt kurumun iletişim e-postasını İÇERMEZ (şema o alanı hiç
taşımıyor). Eşleştirme Ajanı da Faz 2'de bu görünümü okuyacak.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models.ihtiyac_karti import IhtiyacKarti
from app.schemas.tanimlama import IhtiyacKartiYaniti, KurumYaniti

router = APIRouter(tags=["ihtiyac-kartlari"])


async def kart_yaniti(oturum: AsyncSession, kart_id: uuid.UUID) -> IhtiyacKartiYaniti:
    """Kartı kurumuyla okuyup dışarıya açılan şemaya çevirir."""
    kart = await oturum.scalar(
        select(IhtiyacKarti)
        .options(selectinload(IhtiyacKarti.kurum))
        .where(IhtiyacKarti.id == kart_id)
    )
    if kart is None:
        raise HTTPException(status_code=404, detail="İhtiyaç kartı bulunamadı")
    return IhtiyacKartiYaniti(
        id=kart.id,
        problem_tanimi=kart.problem_tanimi,
        basari_kriteri=kart.basari_kriteri,
        kisitlar=kart.kisitlar,
        sehir_tercihi=kart.sehir_tercihi,
        calisma_modeli=kart.calisma_modeli,
        musaitlik_tercihi=kart.musaitlik_tercihi,
        embedding_var=kart.embedding is not None,
        kurum=KurumYaniti(
            id=kart.kurum.id,
            ad=kart.kurum.ad,
            sektor=kart.kurum.sektor,
            sehir=kart.kurum.sehir,
        ),
    )


@router.get("/ihtiyac-kartlari/{kart_id}", response_model=IhtiyacKartiYaniti)
async def ihtiyac_karti_getir(
    kart_id: uuid.UUID, oturum: AsyncSession = Depends(get_session)
) -> IhtiyacKartiYaniti:
    return await kart_yaniti(oturum, kart_id)
