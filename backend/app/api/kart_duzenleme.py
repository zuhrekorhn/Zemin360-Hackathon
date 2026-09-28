"""Yetenek kartı düzenleme uçları (docs/plans/genc-akisi.md § 6.1).

Yalnızca kartın sahibi genç: başkasının kartı ya da iş kalemi 404 (varlık
sızmasın), genç olmayan rol 403, token yok 401. Kural app/agents/kart_duzenleme.py,
uygulama app/servisler/kart_duzenleme.py; burada yetki, işlem ve arka plan işi.

Her gerçek değişiklikte: versiyon artar, yanıttan sonra kart yeniden hazırlanır
(embedding, sıfırlanan kalemin puanı, yeniden eşleştirme). Aynı değerle gelen
düzenleme hiçbir şeyi tetiklemez.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.kart_duzenleme import versiyon_artmali_mi
from app.api.kimlik import rol_gerekli
from app.api.sahiplik import bulunamadi, yetenek_kartinin_sahibi_mi
from app.api.yetenek_kartlari import KART_BULUNAMADI, kart_yaniti
from app.db.session import get_session
from app.models.hesap import ROL_GENC, Hesap
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.kart_duzenleme import IsKalemiGirdisi, IsKalemiGuncelleme, KartGuncelleme
from app.schemas.kesif import YetenekKartiYaniti
from app.servisler import kart_duzenleme as duzenleme
from app.servisler import kart_hazirlama

router = APIRouter(prefix="/yetenek-kartlari", tags=["kart-duzenleme"])

IS_KALEMI_BULUNAMADI = "İş kalemi bulunamadı"


async def _sahibinin_karti(oturum: AsyncSession, hesap: Hesap, kart_id: uuid.UUID) -> YetenekKarti:
    """Kartı kilitleyerek okur (aynı anda iki düzenleme versiyonu ezmesin); sahibi değilse 404."""
    kart = await oturum.scalar(
        select(YetenekKarti)
        .options(
            selectinload(YetenekKarti.somut_ciktilar).selectinload(SomutCikti.guven_skoru),
            selectinload(YetenekKarti.somut_ciktilar).selectinload(SomutCikti.referans_istekleri),
        )
        .where(YetenekKarti.id == kart_id)
        .with_for_update(of=YetenekKarti)
        .execution_options(populate_existing=True)
    )
    if kart is None or not yetenek_kartinin_sahibi_mi(hesap, kart):
        raise bulunamadi(KART_BULUNAMADI)
    return kart


def _is_kalemi(kart: YetenekKarti, cikti_id: uuid.UUID) -> SomutCikti:
    for cikti in kart.somut_ciktilar:
        if cikti.id == cikti_id:
            return cikti
    raise bulunamadi(IS_KALEMI_BULUNAMADI)


async def _sonuclandir(
    oturum: AsyncSession, kart: YetenekKarti, degisti: bool, arka_plan: BackgroundTasks
) -> YetenekKartiYaniti:
    """Değiştiyse versiyon, commit ve yanıttan sonra kart hazırlama."""
    # Kimlik işlem bitmeden alınır: geri almadan sonra nesne süresi dolmuş olur.
    kart_id = kart.id
    if degisti:
        versiyon = await duzenleme.kart_degisti(oturum, kart)
        await oturum.commit()
        arka_plan.add_task(kart_hazirlama.karti_hazirla, kart_id, versiyon, True)
    else:
        await oturum.rollback()  # kilidi bırak
    return await kart_yaniti(oturum, kart_id)


@router.patch("/{kart_id}", response_model=YetenekKartiYaniti)
async def karti_guncelle(
    kart_id: uuid.UUID,
    istek: KartGuncelleme,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> YetenekKartiYaniti:
    """Rol, deneyim, sektör, araçlar, sertifikalar, diller. Doğrulama sıfırlanmaz."""
    kart = await _sahibinin_karti(oturum, hesap, kart_id)
    gonderilen = {alan: getattr(istek, alan) for alan in istek.model_fields_set}
    # Zorunlu kart alanları (rol, deneyim) null gönderilirse yok sayılır.
    gonderilen = {alan: deger for alan, deger in gonderilen.items() if deger is not None}
    degisenler = duzenleme.karti_guncelle(kart, gonderilen)
    return await _sonuclandir(oturum, kart, versiyon_artmali_mi(degisenler), arka_plan)


@router.post("/{kart_id}/ciktilar", response_model=YetenekKartiYaniti, status_code=201)
async def is_kalemi_ekle(
    kart_id: uuid.UUID,
    istek: IsKalemiGirdisi,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> YetenekKartiYaniti:
    kart = await _sahibinin_karti(oturum, hesap, kart_id)
    duzenleme.is_kalemi_ekle(kart, istek.model_dump())
    return await _sonuclandir(oturum, kart, True, arka_plan)


@router.patch("/{kart_id}/ciktilar/{cikti_id}", response_model=YetenekKartiYaniti)
async def is_kalemini_guncelle(
    kart_id: uuid.UUID,
    cikti_id: uuid.UUID,
    istek: IsKalemiGuncelleme,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> YetenekKartiYaniti:
    """İçerik ya da link değişirse o kalemin güven göstergesi sıfırlanır; diğerleri korunur."""
    kart = await _sahibinin_karti(oturum, hesap, kart_id)
    cikti = _is_kalemi(kart, cikti_id)
    gonderilen = {alan: getattr(istek, alan) for alan in istek.model_fields_set}
    if "baslik" in gonderilen and gonderilen["baslik"] is None:
        del gonderilen["baslik"]  # başlık boşaltılamaz
    degisenler = duzenleme.is_kalemini_guncelle(cikti, gonderilen)
    return await _sonuclandir(oturum, kart, versiyon_artmali_mi(degisenler), arka_plan)


@router.delete("/{kart_id}/ciktilar/{cikti_id}", response_model=YetenekKartiYaniti)
async def is_kalemini_sil(
    kart_id: uuid.UUID,
    cikti_id: uuid.UUID,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> YetenekKartiYaniti:
    kart = await _sahibinin_karti(oturum, hesap, kart_id)
    duzenleme.is_kalemini_sil(kart, _is_kalemi(kart, cikti_id))
    return await _sonuclandir(oturum, kart, True, arka_plan)
