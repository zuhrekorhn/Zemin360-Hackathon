"""Tanımlama Ajanı uç noktaları (docs/api-contracts.md § Tanımlama).

Keşif ile aynı desen: sohbet durumu LangGraph checkpointer'ında, `oturum_id`
thread_id olarak kullanılıyor.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.sohbet_motoru import HizSinirHatasi, kullanici_mesaji
from app.api.eslestirme import eslestirmeyi_arka_planda_calistir
from app.api.ihtiyac_kartlari import kart_yaniti
from app.core.embeddings import embedding_uret, ihtiyac_temsil_metni
from app.core.sehir import sehir_kanonik
from app.db.session import get_session
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kurum import Kurum
from app.schemas.sohbet import SohbetBaslatIstegi, SohbetCevapIstegi
from app.schemas.tanimlama import (
    IhtiyacKartiOnaylaIstegi,
    IhtiyacKartiYaniti,
    IhtiyacTaslagi,
    TanimlamaSohbetYaniti,
)

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
async def sohbet_baslat(_: SohbetBaslatIstegi, request: Request) -> TanimlamaSohbetYaniti:
    oturum_id = uuid.uuid4()
    durum = await _grafik(request).ainvoke(
        {}, config={"configurable": {"thread_id": str(oturum_id)}}
    )
    return _yanit(oturum_id, durum)


@router.post("/sohbet/cevap", response_model=TanimlamaSohbetYaniti)
async def sohbet_cevap(istek: SohbetCevapIstegi, request: Request) -> TanimlamaSohbetYaniti:
    config = {"configurable": {"thread_id": str(istek.oturum_id)}}
    grafik = _grafik(request)

    mevcut = await grafik.aget_state(config)
    if not mevcut.values:
        raise HTTPException(status_code=404, detail="Sohbet oturumu bulunamadı")
    if mevcut.values.get("taslak_hazir"):
        raise HTTPException(status_code=409, detail="Taslak hazır; sıradaki adım onay")

    try:
        durum = await grafik.ainvoke({"mesajlar": [kullanici_mesaji(istek.cevap)]}, config=config)
    except HizSinirHatasi as hata:
        raise HTTPException(
            status_code=429,
            detail="LLM kotası doldu, biraz sonra tekrar dene. Sohbetin kayıtlı.",
        ) from hata

    return _yanit(istek.oturum_id, durum)


@router.post("/kart/onayla", response_model=IhtiyacKartiYaniti, status_code=201)
async def kart_onayla(
    istek: IhtiyacKartiOnaylaIstegi,
    request: Request,
    arka_plan: BackgroundTasks,
    oturum: AsyncSession = Depends(get_session),
) -> IhtiyacKartiYaniti:
    """Onaylanan taslağı IHTIYAC_KARTI'na yazar, ardından embedding'ini hesaplar."""
    config = {"configurable": {"thread_id": str(istek.oturum_id)}}
    mevcut = await _grafik(request).aget_state(config)
    if not mevcut.values:
        raise HTTPException(status_code=404, detail="Sohbet oturumu bulunamadı")
    if not mevcut.values.get("taslak_hazir"):
        raise HTTPException(status_code=409, detail="Taslak henüz hazır değil")

    taslak = istek.duzeltilmis_taslak or IhtiyacTaslagi(**mevcut.values["taslak"])
    if not taslak.problem_tanimi:
        raise HTTPException(status_code=422, detail="Taslakta problem tanımı zorunlu")

    kurum = await _kurumu_bul_veya_olustur(oturum, istek)

    kart = IhtiyacKarti(
        kurum_id=kurum.id,
        problem_tanimi=taslak.problem_tanimi,
        basari_kriteri=taslak.basari_kriteri,
        kisitlar=taslak.kisitlar,
        sehir_tercihi=sehir_kanonik(taslak.sehir_tercihi),
        musaitlik_tercihi=taslak.musaitlik_tercihi,
    )
    oturum.add(kart)
    await oturum.commit()

    # Kart kaydedildikten SONRA embedding (docs/matching-algorithm.md § 1-2).
    kart.embedding = await embedding_uret(
        ihtiyac_temsil_metni(
            problem_tanimi=kart.problem_tanimi, basari_kriteri=kart.basari_kriteri
        ),
        girdi_turu="document",
    )
    await oturum.commit()

    # Eşleştirme yanıt gönderildikten sonra başlıyor: kurum öneriler sayfasına
    # geldiğinde hesap çoğunlukla hazır olur.
    arka_plan.add_task(eslestirmeyi_arka_planda_calistir, kurum.id)

    return await kart_yaniti(oturum, kart.id)


async def _kurumu_bul_veya_olustur(oturum: AsyncSession, istek: IhtiyacKartiOnaylaIstegi) -> Kurum:
    girdi = istek.kurum
    kurum = await oturum.scalar(
        select(Kurum).where(Kurum.iletisim_email == str(girdi.iletisim_email))
    )
    if kurum is None:
        kurum = Kurum(
            ad=girdi.ad,
            sektor=girdi.sektor,
            sehir=sehir_kanonik(girdi.sehir),
            iletisim_email=str(girdi.iletisim_email),
        )
        oturum.add(kurum)
        await oturum.flush()
    return kurum
