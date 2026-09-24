"""Yetenek kartı okuma uç noktası.

Gizlilik (docs/agent-specs.md § 1.5): bu yanıt kullanıcının e-postasını ve
diğer iletişim bilgilerini İÇERMEZ — kart görünür, iletişim iki taraf da
onaylayınca açılır. Şema (app/schemas/kesif.py) bu alanları hiç taşımıyor,
yani yanlışlıkla sızdırmak için şemayı değiştirmek gerekir.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.kesif import YetenekKartiYaniti

router = APIRouter(tags=["yetenek-kartlari"])


async def kart_yaniti(oturum: AsyncSession, kart_id: uuid.UUID) -> YetenekKartiYaniti:
    """Kartı ilişkileriyle okuyup dışarıya açılan şemaya çevirir.

    Keşif Ajanı da onay sonrası yanıtı bunun üzerinden döner — iki uç noktanın
    aynı kartı farklı alanlarla göstermemesi için tek yer.
    """
    kart = await oturum.scalar(
        select(YetenekKarti)
        .options(selectinload(YetenekKarti.somut_ciktilar).selectinload(SomutCikti.guven_skoru))
        .where(YetenekKarti.id == kart_id)
    )
    if kart is None:
        raise HTTPException(status_code=404, detail="Yetenek kartı bulunamadı")
    return YetenekKartiYaniti(
        id=kart.id,
        rol_alani=kart.rol_alani,
        deneyim_seviyesi=kart.deneyim_seviyesi,
        sektor_ilgi_alani=kart.sektor_ilgi_alani,
        araclar_teknolojiler=kart.araclar_teknolojiler,
        kanit_bekleyen=kart.kanit_bekleyen,
        versiyon=kart.versiyon,
        embedding_var=kart.embedding is not None,
        somut_ciktilar=kart.somut_ciktilar,
    )


@router.get("/yetenek-kartlari/{kart_id}", response_model=YetenekKartiYaniti)
async def yetenek_karti_getir(
    kart_id: uuid.UUID, oturum: AsyncSession = Depends(get_session)
) -> YetenekKartiYaniti:
    return await kart_yaniti(oturum, kart_id)
