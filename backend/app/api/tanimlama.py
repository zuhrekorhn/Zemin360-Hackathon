"""Tanımlama Ajanı uç noktaları (docs/api-contracts.md § Tanımlama).

Keşif ile aynı desen: sohbet durumu LangGraph checkpointer'ında, `oturum_id`
thread_id olarak kullanılıyor.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.sohbet_motoru import HizSinirHatasi, kullanici_mesaji
from app.api.ihtiyac_kartlari import embedding_hesapla, kart_yaniti
from app.api.kimlik import rol_gerekli
from app.api.profil import kurumun_profilini_guncelle
from app.api.sahiplik import sohbet_baslangici, sohbetin_sahibi_mi
from app.core import calisma_modeli
from app.core.hatalar import HIZ_SINIRI_MESAJI
from app.core.sehir import sehir_kanonik
from app.db.session import get_session
from app.models.hesap import ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.schemas.sohbet import SohbetBaslatIstegi, SohbetCevapIstegi
from app.schemas.tanimlama import (
    IhtiyacKartiOnaylaIstegi,
    IhtiyacKartiYaniti,
    IhtiyacTaslagi,
    TanimlamaSohbetYaniti,
)
from app.servisler.eslestirme import eslestirmeyi_arka_planda_calistir

router = APIRouter(prefix="/tanimlama", tags=["tanimlama"])


def _grafik(request: Request):
    grafik = getattr(request.app.state, "tanimlama_grafigi", None)
    if grafik is None:
        raise HTTPException(status_code=503, detail="Tanımlama Ajanı hazır değil")
    return grafik


def _yanit(oturum_id: uuid.UUID, durum: dict) -> TanimlamaSohbetYaniti:
    return TanimlamaSohbetYaniti(
        oturum_id=oturum_id,
        soru=durum.get("sonraki_soru"),
        taslak=IhtiyacTaslagi(**(durum.get("taslak") or {})),
        taslak_hazir=bool(durum.get("taslak_hazir")),
    )


@router.post("/sohbet/baslat", response_model=TanimlamaSohbetYaniti)
async def sohbet_baslat(
    _: SohbetBaslatIstegi, request: Request, hesap: Hesap = Depends(rol_gerekli(ROL_KURUM))
) -> TanimlamaSohbetYaniti:
    oturum_id = uuid.uuid4()
    # Oturumu açan hesap checkpoint'e yazılır; cevap ve onay yalnızca ondan.
    durum = await _grafik(request).ainvoke(
        sohbet_baslangici(hesap), config={"configurable": {"thread_id": str(oturum_id)}}
    )
    return _yanit(oturum_id, durum)


@router.post("/sohbet/cevap", response_model=TanimlamaSohbetYaniti)
async def sohbet_cevap(
    istek: SohbetCevapIstegi, request: Request, hesap: Hesap = Depends(rol_gerekli(ROL_KURUM))
) -> TanimlamaSohbetYaniti:
    config = {"configurable": {"thread_id": str(istek.oturum_id)}}
    grafik = _grafik(request)

    mevcut = await grafik.aget_state(config)
    if not mevcut.values or not sohbetin_sahibi_mi(mevcut.values, hesap):
        raise HTTPException(status_code=404, detail="Sohbet oturumu bulunamadı")
    if mevcut.values.get("taslak_hazir"):
        raise HTTPException(status_code=409, detail="Taslak hazır; sıradaki adım onay")

    try:
        durum = await grafik.ainvoke({"mesajlar": [kullanici_mesaji(istek.cevap)]}, config=config)
    except HizSinirHatasi as hata:
        raise HTTPException(
            status_code=429,
            detail=f"{HIZ_SINIRI_MESAJI} Sohbetin kayıtlı.",
        ) from hata

    return _yanit(istek.oturum_id, durum)


@router.post("/kart/onayla", response_model=IhtiyacKartiYaniti, status_code=201)
async def kart_onayla(
    istek: IhtiyacKartiOnaylaIstegi,
    request: Request,
    arka_plan: BackgroundTasks,
    yanit: Response,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> IhtiyacKartiYaniti:
    """Onaylanan taslağı IHTIYAC_KARTI'na yazar, ardından embedding'ini hesaplar.

    Keşif'teki gibi tekrarlanabilir: aynı `oturum_id` ikinci kez onaylanırsa
    mevcut kart 200 ile döner, embedding'i eksikse yeniden denenir.
    """
    config = {"configurable": {"thread_id": str(istek.oturum_id)}}
    mevcut = await _grafik(request).aget_state(config)
    if not mevcut.values or not sohbetin_sahibi_mi(mevcut.values, hesap):
        raise HTTPException(status_code=404, detail="Sohbet oturumu bulunamadı")

    onceki = await _oturumun_karti(oturum, istek.oturum_id)
    if onceki is not None:
        yanit.status_code = 200
        return await _mevcut_karti_don(oturum, onceki, arka_plan)

    if not mevcut.values.get("taslak_hazir"):
        raise HTTPException(status_code=409, detail="Taslak henüz hazır değil")

    taslak = istek.duzeltilmis_taslak or IhtiyacTaslagi(**mevcut.values["taslak"])
    if not taslak.problem_tanimi:
        raise HTTPException(status_code=422, detail="Taslakta problem tanımı zorunlu")

    # Kart token'daki hesabın kurumuna bağlanır (docs/faz-b-kimlik-ve-dongu.md § 4).
    kurum_id = hesap.kurum.id
    kurumun_profilini_guncelle(hesap.kurum, istek.kurum_profili)

    kart = IhtiyacKarti(
        oturum_id=istek.oturum_id,
        kurum_id=kurum_id,
        problem_tanimi=taslak.problem_tanimi,
        basari_kriteri=taslak.basari_kriteri,
        kisitlar=taslak.kisitlar,
        sehir_tercihi=sehir_kanonik(taslak.sehir_tercihi),
        calisma_modeli=(
            taslak.calisma_modeli if calisma_modeli.gecerli_mi(taslak.calisma_modeli) else None
        ),
        musaitlik_tercihi=taslak.musaitlik_tercihi,
    )
    oturum.add(kart)
    try:
        await oturum.commit()
    except IntegrityError:
        # Aynı oturum için eşzamanlı ikinci onay: diğer istek kartı yazdı.
        await oturum.rollback()
        onceki = await _oturumun_karti(oturum, istek.oturum_id)
        if onceki is None:
            raise
        yanit.status_code = 200
        return await _mevcut_karti_don(oturum, onceki, arka_plan)

    # Kart kaydedildikten SONRA embedding (docs/matching-algorithm.md § 1-2).
    # Voyage'a ulaşılamazsa kart kaybolmaz; eşleştirme de başlamaz, çünkü
    # embedding'siz kart aday bulamaz. Arayüz yeniden hesaplatmayı önerir.
    if await embedding_hesapla(oturum, kart):
        # Yanıt gönderildikten sonra başlıyor: kurum öneriler sayfasına
        # geldiğinde hesap çoğunlukla hazır olur.
        arka_plan.add_task(eslestirmeyi_arka_planda_calistir, kart.id)

    return await kart_yaniti(oturum, kart.id)


async def _oturumun_karti(oturum: AsyncSession, oturum_id: uuid.UUID) -> IhtiyacKarti | None:
    return await oturum.scalar(select(IhtiyacKarti).where(IhtiyacKarti.oturum_id == oturum_id))


async def _mevcut_karti_don(
    oturum: AsyncSession, kart: IhtiyacKarti, arka_plan: BackgroundTasks
) -> IhtiyacKartiYaniti:
    """Daha önce onaylanmış kartı döner; embedding'i eksikse bir kez daha dener."""
    if kart.embedding is None and await embedding_hesapla(oturum, kart):
        arka_plan.add_task(eslestirmeyi_arka_planda_calistir, kart.id)
    return await kart_yaniti(oturum, kart.id)
