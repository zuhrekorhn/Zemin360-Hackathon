"""Uygulama içi bildirimler (docs/faz-b-kimlik-ve-dongu.md § 6).

Bildirimi olayın kendisi yazar (eşleşme geçişi, pipeline, referans yanıtı),
aynı işlemde: olay olup bildirim kaybolmasın, bildirim olup olay geri
alınmasın. Gerçek e-posta yok; okunmamış sayısı `GET /me`'de.
"""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.kimlik import mevcut_hesap
from app.api.sahiplik import bulunamadi
from app.db.session import get_session
from app.models.bildirim import Bildirim
from app.models.eslesme import Eslesme
from app.models.hesap import Hesap
from app.schemas.bildirim import BildirimYaniti, HepsiniOkuYaniti

router = APIRouter(prefix="/bildirimler", tags=["bildirimler"])

# Liste sayfalanmıyor; bu kadarı bir panelde fazlasıyla yeter.
LISTE_SINIRI = 100
BILDIRIM_BULUNAMADI = "Bildirim bulunamadı"


def bildirim_ekle(
    oturum: AsyncSession,
    hesap_id: uuid.UUID | None,
    tur: str,
    metin: str,
    eslesme_id: uuid.UUID | None = None,
) -> None:
    """Bildirimi oturuma ekler; commit çağıranın işi (olayla aynı işlem).

    Hesabı olmayan profil (Faz B öncesi kayıt) için sessizce atlanır:
    okuyacak kimse yok.
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
