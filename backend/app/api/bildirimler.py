"""Uygulama içi bildirimlerin okuma uçları (docs/faz-b-kimlik-ve-dongu.md § 6).

Bildirimi yazan ve sayan fonksiyonlar `app/servisler/bildirim.py`'de: bildirimi
olayın kendisi, olayla aynı işlemde yazar.
"""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.kimlik import bulunamadi, mevcut_hesap
from app.db.session import get_session
from app.models.bildirim import Bildirim
from app.models.eslesme import Eslesme
from app.models.hesap import Hesap
from app.schemas.bildirim import BildirimYaniti, HepsiniOkuYaniti

router = APIRouter(prefix="/bildirimler", tags=["bildirimler"])

# Liste sayfalanmıyor; bu kadarı bir panelde fazlasıyla yeter.
LISTE_SINIRI = 100
BILDIRIM_BULUNAMADI = "Bildirim bulunamadı"


@router.get("", response_model=list[BildirimYaniti])
async def bildirimler(
    hesap: Hesap = Depends(mevcut_hesap), oturum: AsyncSession = Depends(get_session)
) -> list[BildirimYaniti]:
    """Hesabın bildirimleri, en yeni önce; iş birliği varsa kimliğiyle."""
    satirlar = await oturum.scalars(
        select(Bildirim)
        .options(selectinload(Bildirim.eslesme).selectinload(Eslesme.isbirligi))
        .where(Bildirim.hesap_id == hesap.id)
        .order_by(Bildirim.olusturma_tarihi.desc(), Bildirim.id)
        .limit(LISTE_SINIRI)
    )
    return [
        BildirimYaniti.model_validate(bildirim).model_copy(
            update={
                "isbirligi_id": bildirim.eslesme.isbirligi.id
                if bildirim.eslesme is not None and bildirim.eslesme.isbirligi is not None
                else None
            }
        )
        for bildirim in satirlar.all()
    ]


@router.post("/hepsini-oku", response_model=HepsiniOkuYaniti)
async def hepsini_oku(
    hesap: Hesap = Depends(mevcut_hesap), oturum: AsyncSession = Depends(get_session)
) -> HepsiniOkuYaniti:
    sonuc = await oturum.execute(
        update(Bildirim)
        .where(Bildirim.hesap_id == hesap.id, Bildirim.okundu_tarihi.is_(None))
        .values(okundu_tarihi=dt.datetime.now(dt.UTC))
    )
    await oturum.commit()
    return HepsiniOkuYaniti(okunan=sonuc.rowcount)


@router.post("/{bildirim_id}/okundu", response_model=BildirimYaniti)
async def okundu(
    bildirim_id: uuid.UUID,
    hesap: Hesap = Depends(mevcut_hesap),
    oturum: AsyncSession = Depends(get_session),
) -> Bildirim:
    """Tekrar çağrılırsa ilk okunma tarihi korunur. Başkasının bildirimi 404."""
    bildirim = await oturum.get(Bildirim, bildirim_id)
    if bildirim is None or bildirim.hesap_id != hesap.id:
        raise bulunamadi(BILDIRIM_BULUNAMADI)
    if bildirim.okundu_tarihi is None:
        bildirim.okundu_tarihi = dt.datetime.now(dt.UTC)
        await oturum.commit()
    return bildirim
