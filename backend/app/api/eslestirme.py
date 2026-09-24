"""Eşleştirme Ajanı uç noktaları (docs/api-contracts.md § Eşleştirme).

`/eslestirme/calistir` sözleşmede "arka plan işi" olarak geçiyor: Genç ile
Kurum aynı anda platformda olmak zorunda değil. Gerçek bir cron/kuyruk
altyapısı kurmuyoruz (bilinçli, bkz. docs/architecture.md) — bu uç nokta
ileride bir zamanlayıcının çağıracağı "asıl işi yapan" kanca; şimdilik
doğrudan da çağrılabiliyor.
"""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.eslestirme import (
    DURUM_KABUL_EDILDI,
    DURUM_ONERILDI,
    SKOR_ESIGI,
    TOP_N,
    Aday,
    adaylari_getir,
    gerekce_uret,
    ihtiyac_kartini_getir,
    siralayip_ele,
    temizlenecekler,
)
from app.api.yetenek_kartlari import kart_yaniti
from app.core.llm import HizSinirHatasi
from app.db.session import get_session
from app.models.eslesme import Eslesme
from app.models.isbirligi import Isbirligi
from app.schemas.eslestirme import (
    EslestirmeCalistirIstegi,
    IlgileniyorumIstegi,
    IlgileniyorumYaniti,
    OnerilerYaniti,
    OneriYaniti,
)

router = APIRouter(prefix="/eslestirme", tags=["eslestirme"])

ISBIRLIGI_AKTIF = "aktif"


@router.post("/calistir", response_model=OnerilerYaniti)
async def calistir(
    istek: EslestirmeCalistirIstegi, oturum: AsyncSession = Depends(get_session)
) -> OnerilerYaniti:
    return await _pipeline_calistir(oturum, istek.kurum_id)


@router.get("/oneriler/{kurum_id}", response_model=OnerilerYaniti)
async def oneriler(
    kurum_id: uuid.UUID, oturum: AsyncSession = Depends(get_session)
) -> OnerilerYaniti:
    """Hesaplanmış önerileri sıralı döner; hiç hesaplanmamışsa pipeline'ı tetikler."""
    ihtiyac = await ihtiyac_kartini_getir(oturum, kurum_id)
    if ihtiyac is None:
        raise HTTPException(status_code=404, detail="Kuruma ait ihtiyaç kartı yok")

    mevcut = await _eslesmeleri_oku(oturum, ihtiyac.id)
    if not mevcut:
        return await _pipeline_calistir(oturum, kurum_id)

    return await _yanit_kur(oturum, ihtiyac.id, mevcut)


@router.post("/ilgileniyorum", response_model=IlgileniyorumYaniti)
async def ilgileniyorum(
    istek: IlgileniyorumIstegi, oturum: AsyncSession = Depends(get_session)
) -> IlgileniyorumYaniti:
    """Kurum ilgilendiğini söyler: eşleşme kabul edilir, iş birliği açılır.

    Ayrı bir kabul adımı yok — MVP kararı. Genç'e bildirim gitmesi Faz 3+
    kapsamında (şu an bilinçli olarak yok).
    """
    eslesme = await oturum.scalar(
        select(Eslesme)
        .options(selectinload(Eslesme.isbirligi))
        .where(Eslesme.id == istek.eslesme_id)
    )
    if eslesme is None:
        raise HTTPException(status_code=404, detail="Eşleşme bulunamadı")

    eslesme.durum = DURUM_KABUL_EDILDI
    eslesme.son_aktivite_tarihi = dt.datetime.now(dt.UTC)

    isbirligi = eslesme.isbirligi
    if isbirligi is None:
        isbirligi = Isbirligi(
            eslesme_id=eslesme.id,
            baslangic_tarihi=dt.date.today(),
            durum=ISBIRLIGI_AKTIF,
        )
        oturum.add(isbirligi)

    await oturum.commit()

    return IlgileniyorumYaniti(
        eslesme_id=eslesme.id,
        durum=eslesme.durum,
        isbirligi_id=isbirligi.id,
        isbirligi_durum=isbirligi.durum,
    )


# --- Pipeline --------------------------------------------------------------


async def _pipeline_calistir(oturum: AsyncSession, kurum_id: uuid.UUID) -> OnerilerYaniti:
    ihtiyac = await ihtiyac_kartini_getir(oturum, kurum_id)
    if ihtiyac is None:
        raise HTTPException(status_code=404, detail="Kuruma ait ihtiyaç kartı yok")
    if ihtiyac.embedding is None:
        raise HTTPException(
            status_code=409, detail="İhtiyaç kartının embedding'i yok; kart yeniden onaylanmalı"
        )

    secilenler = siralayip_ele(await adaylari_getir(oturum, ihtiyac))
    eskiler = await _eslesmeleri_oku(oturum, ihtiyac.id)
    mevcutlar = {e.yetenek_karti_id: e for e in eskiler}

    # Kural ya da kart değişmiş olabilir: artık seçilmeyen öneriler listede
    # kalmasın. Kurumun karar verdiği kayıtlara dokunulmuyor.
    for eskimis in temizlenecekler(eskiler, [aday.yetenek_karti.id for aday in secilenler]):
        mevcutlar.pop(eskimis.yetenek_karti_id, None)
        await oturum.delete(eskimis)

    for aday in secilenler:
        eslesme = mevcutlar.get(aday.yetenek_karti.id)
        if eslesme is None:
            eslesme = Eslesme(
                yetenek_karti_id=aday.yetenek_karti.id,
                ihtiyac_karti_id=ihtiyac.id,
                skor=aday.skor,
                durum=DURUM_ONERILDI,
            )
            oturum.add(eslesme)
            mevcutlar[aday.yetenek_karti.id] = eslesme
        else:
            # Kurumun verdiği karar (ilgileniliyor/kabul/red) ezilmez;
            # yalnızca skor tazelenir.
            eslesme.skor = aday.skor

        if eslesme.gerekce_metni is None:
            eslesme.gerekce_metni = await _gerekce(ihtiyac, aday)

    await oturum.commit()

    return await _yanit_kur(oturum, ihtiyac.id, await _eslesmeleri_oku(oturum, ihtiyac.id))


async def _gerekce(ihtiyac, aday: Aday) -> str | None:
    """Gerekçeyi üretir; LLM kotası dolduysa eşleşmeyi gerekçesiz bırakır.

    Skor ve sıralama LLM'den bağımsız — kota yüzünden tüm öneri listesini
    kaybetmek mantıksız olurdu. Gerekçe NULL kalır, sonraki çalıştırmada
    yeniden denenir.
    """
    try:
        return await gerekce_uret(ihtiyac, aday)
    except HizSinirHatasi:
        return None


async def _eslesmeleri_oku(oturum: AsyncSession, ihtiyac_karti_id: uuid.UUID) -> list[Eslesme]:
    satirlar = await oturum.scalars(
        select(Eslesme)
        .where(Eslesme.ihtiyac_karti_id == ihtiyac_karti_id)
        .order_by(Eslesme.skor.desc())
    )
    return list(satirlar)


async def _yanit_kur(
    oturum: AsyncSession, ihtiyac_karti_id: uuid.UUID, eslesmeler: list[Eslesme]
) -> OnerilerYaniti:
    oneriler = [
        OneriYaniti(
            eslesme_id=eslesme.id,
            skor=round(eslesme.skor, 4),
            durum=eslesme.durum,
            gerekce_metni=eslesme.gerekce_metni,
            yetenek_karti=await kart_yaniti(oturum, eslesme.yetenek_karti_id),
        )
        for eslesme in eslesmeler
    ]
    return OnerilerYaniti(
        ihtiyac_karti_id=ihtiyac_karti_id,
        oneriler=oneriler,
        # Cold start: havuz küçükken bunu arayüzde gizleme (matching-algorithm.md § 5)
        az_sonuc_uyarisi=len(oneriler) < TOP_N,
        skor_esigi=SKOR_ESIGI,
    )
