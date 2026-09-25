"""İhtiyaç kartı okuma ve embedding uç noktaları.

Gizlilik: yanıt kurumun iletişim e-postasını İÇERMEZ (şema o alanı hiç
taşımıyor). Eşleştirme Ajanı da bu görünümü okuyor.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.eslestirme import eslestirmeyi_arka_planda_calistir
from app.api.kimlik import mevcut_hesap
from app.api.sahiplik import (
    bulunamadi,
    girvak_mi,
    ihtiyac_kartini_gorebilir_mi,
    ihtiyac_kartinin_sahibi_mi,
)
from app.api.yetenek_kartlari import EMBEDDING_HATA_MESAJI
from app.core.embeddings import EmbeddingHatasi, embedding_uret, ihtiyac_temsil_metni
from app.db.session import get_session
from app.models.hesap import Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.schemas.tanimlama import IhtiyacKartiYaniti, KurumYaniti

logger = logging.getLogger("zemin360.embedding")

router = APIRouter(tags=["ihtiyac-kartlari"])

KART_BULUNAMADI = "İhtiyaç kartı bulunamadı"


async def kart_yaniti(oturum: AsyncSession, kart_id: uuid.UUID) -> IhtiyacKartiYaniti:
    """Kartı kurumuyla okuyup dışarıya açılan şemaya çevirir."""
    kart = await oturum.scalar(
        select(IhtiyacKarti)
        .options(selectinload(IhtiyacKarti.kurum))
        .where(IhtiyacKarti.id == kart_id)
    )
    if kart is None:
        raise bulunamadi(KART_BULUNAMADI)
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


async def embedding_hesapla(oturum: AsyncSession, kart: IhtiyacKarti) -> bool:
    """İhtiyaç kartının embedding'ini hesaplayıp kaydeder.

    Yetenek kartındakiyle aynı sözleşme (app/api/yetenek_kartlari.py):
    Voyage'a ulaşılamazsa False döner, kart kaybolmaz.
    """
    metin = ihtiyac_temsil_metni(
        problem_tanimi=kart.problem_tanimi, basari_kriteri=kart.basari_kriteri
    )
    try:
        kart.embedding = await embedding_uret(metin, girdi_turu="document")
    except EmbeddingHatasi:
        logger.warning("İhtiyaç kartı embedding'i hesaplanamadı (%s)", kart.id, exc_info=True)
        return False
    await oturum.commit()
    return True


@router.get("/ihtiyac-kartlari/{kart_id}", response_model=IhtiyacKartiYaniti)
async def ihtiyac_karti_getir(
    kart_id: uuid.UUID,
    hesap: Hesap = Depends(mevcut_hesap),
    oturum: AsyncSession = Depends(get_session),
) -> IhtiyacKartiYaniti:
    """Kurum kendi kartını, genç kendisine ilgi gösterilmiş ihtiyacı, GİRVAK hepsini görür."""
    kart = await oturum.get(IhtiyacKarti, kart_id)
    if kart is None or not await ihtiyac_kartini_gorebilir_mi(oturum, hesap, kart):
        raise bulunamadi(KART_BULUNAMADI)
    return await kart_yaniti(oturum, kart_id)


@router.post("/ihtiyac-kartlari/{kart_id}/embedding", response_model=IhtiyacKartiYaniti)
async def ihtiyac_karti_embedding(
    kart_id: uuid.UUID,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(mevcut_hesap),
    oturum: AsyncSession = Depends(get_session),
) -> IhtiyacKartiYaniti:
    """Embedding'i yeniden hesaplar; başarılıysa eşleştirmeyi de başlatır.

    Onayda Voyage'a ulaşılamadıysa eşleştirme de hiç başlamamıştı — kart
    ancak embedding'i olunca aday bulabiliyor.
    """
    kart = await oturum.scalar(select(IhtiyacKarti).where(IhtiyacKarti.id == kart_id))
    if kart is None or not (girvak_mi(hesap) or ihtiyac_kartinin_sahibi_mi(hesap, kart)):
        raise bulunamadi(KART_BULUNAMADI)
    if not await embedding_hesapla(oturum, kart):
        raise HTTPException(status_code=503, detail=EMBEDDING_HATA_MESAJI)
    arka_plan.add_task(eslestirmeyi_arka_planda_calistir, kart.kurum_id)
    return await kart_yaniti(oturum, kart.id)
