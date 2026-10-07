"""GİRVAK inceleme kuyruğu uçları (docs/dogrulama.md § 9).

Yalnızca GİRVAK. Liste ve karar; işaret açmak bu uçların işi değil, sinyali
gören servisin (itiraz, ad değişikliği talebi, ileride kanıt işaretleri).
Orkestrasyon `app/servisler/inceleme.py`'de.
"""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.inceleme_durumu import ACIK, GecersizKarar
from app.api.kimlik import bulunamadi, rol_gerekli
from app.db.session import get_session
from app.models.hesap import ROL_GIRVAK
from app.models.inceleme_isareti import IncelemeIsareti
from app.models.kullanici import Kullanici
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.girvak import IncelemeKarariIstegi, IncelemeSatiri
from app.servisler import inceleme
from app.servisler.inceleme_isleyicileri import isleyici

router = APIRouter(
    prefix="/girvak/inceleme",
    tags=["girvak"],
    dependencies=[Depends(rol_gerekli(ROL_GIRVAK))],
)

ISARET_BULUNAMADI = "İşaret bulunamadı"


def _sorgu():
    return (
        select(IncelemeIsareti, Kullanici.ad, YetenekKarti.id, SomutCikti.baslik)
        .join(Kullanici, Kullanici.id == IncelemeIsareti.kullanici_id)
        .outerjoin(YetenekKarti, YetenekKarti.kullanici_id == Kullanici.id)
        .outerjoin(SomutCikti, SomutCikti.id == IncelemeIsareti.somut_cikti_id)
    )


def _satir(isaret: IncelemeIsareti, ad, kart_id, baslik) -> IncelemeSatiri:
    return IncelemeSatiri(
        id=isaret.id,
        tur=isaret.tur,
        durum=isaret.durum,
        olusturma_tarihi=isaret.olusturma_tarihi,
        kapanma_tarihi=isaret.kapanma_tarihi,
        girvak_notu=isaret.girvak_notu,
        genc_adi=ad,
        kart_id=kart_id,
        somut_cikti_id=isaret.somut_cikti_id,
        cikti_basligi=baslik,
        ayrinti=isaret.ayrinti or {},
    )


@router.get("", response_model=list[IncelemeSatiri])
async def isaretler(
    durum: Literal["acik", "kapandi", "dogrulanamadi"] = ACIK,
    oturum: AsyncSession = Depends(get_session),
) -> list[IncelemeSatiri]:
    """Açık işaretler en eski önce (kuyruk); kapananlar en yeni karar önce."""
    sira = (
        IncelemeIsareti.olusturma_tarihi.asc()
        if durum == ACIK
        else IncelemeIsareti.kapanma_tarihi.desc()
    )
    satirlar = await oturum.execute(_sorgu().where(IncelemeIsareti.durum == durum).order_by(sira))
    return [_satir(*satir) for satir in satirlar.all()]


@router.post("/{isaret_id}/karar", response_model=IncelemeSatiri)
async def karar(
    isaret_id: uuid.UUID,
    istek: IncelemeKarariIstegi,
    arka_plan: BackgroundTasks,
    oturum: AsyncSession = Depends(get_session),
) -> IncelemeSatiri:
    """Aynı kararın tekrarı 200 ve yan etkisiz; kapanmış işarete başka karar 409.
    Gence bildirim kararla aynı işlemde yazılır."""
    isaret = await oturum.scalar(
        select(IncelemeIsareti).where(IncelemeIsareti.id == isaret_id).with_for_update()
    )
    if isaret is None:
        raise bulunamadi(ISARET_BULUNAMADI)
    try:
        isler = await inceleme.karar_ver(
            oturum, isaret, istek.karar, istek.girvak_notu, isleyici(isaret.tur)
        )
    except GecersizKarar as hata:
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    await oturum.commit()
    for is_ in isler:
        arka_plan.add_task(is_.fonksiyon, *is_.argumanlar)
    satir = (await oturum.execute(_sorgu().where(IncelemeIsareti.id == isaret_id))).one()
    return _satir(*satir)
