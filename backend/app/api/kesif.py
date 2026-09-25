"""Keşif Ajanı uç noktaları (docs/api-contracts.md § Keşif).

Sohbet durumu LangGraph'ın Postgres checkpointer'ında, `oturum_id` de
thread_id olarak tutulur — uygulama tarafında ayrı bir oturum tablosu yok.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.kesif import HizSinirHatasi, kullanici_mesaji
from app.api.yetenek_kartlari import embedding_hesapla, kart_yaniti
from app.core import calisma_modeli
from app.core.sehir import sehir_kanonik
from app.db.session import get_session
from app.models.kullanici import Kullanici
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.kesif import (
    KartOnaylaIstegi,
    KartTaslagi,
    SohbetBaslatIstegi,
    SohbetCevapIstegi,
    SohbetYaniti,
    YetenekKartiYaniti,
)

router = APIRouter(prefix="/kesif", tags=["kesif"])


def _grafik(request: Request):
    grafik = getattr(request.app.state, "kesif_grafigi", None)
    if grafik is None:
        # Checkpointer uygulama açılışında kuruluyor; kurulamadıysa sessizce
        # bozuk bir sohbet yürütmek yerine açıkça söyle.
        raise HTTPException(status_code=503, detail="Keşif Ajanı hazır değil")
    return grafik


def _yanit(oturum_id: uuid.UUID, durum: dict) -> SohbetYaniti:
    return SohbetYaniti(
        oturum_id=oturum_id,
        soru=durum.get("sonraki_soru"),
        taslak=KartTaslagi(**(durum.get("taslak") or {})),
        taslak_hazir=bool(durum.get("taslak_hazir")),
    )


@router.post("/sohbet/baslat", response_model=SohbetYaniti)
async def sohbet_baslat(_: SohbetBaslatIstegi, request: Request) -> SohbetYaniti:
    oturum_id = uuid.uuid4()
    durum = await _grafik(request).ainvoke(
        {}, config={"configurable": {"thread_id": str(oturum_id)}}
    )
    return _yanit(oturum_id, durum)


@router.post("/sohbet/cevap", response_model=SohbetYaniti)
async def sohbet_cevap(istek: SohbetCevapIstegi, request: Request) -> SohbetYaniti:
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
        # Sohbet durumu checkpointer'da duruyor; kullanıcı biraz sonra aynı
        # oturum_id ile kaldığı yerden devam edebilir.
        raise HTTPException(
            status_code=429,
            detail="LLM kotası doldu, biraz sonra tekrar dene. Sohbetin kayıtlı.",
        ) from hata

    return _yanit(istek.oturum_id, durum)


@router.post("/kart/onayla", response_model=YetenekKartiYaniti, status_code=201)
async def kart_onayla(
    istek: KartOnaylaIstegi,
    request: Request,
    yanit: Response,
    oturum: AsyncSession = Depends(get_session),
) -> YetenekKartiYaniti:
    """Onaylanan taslağı YETENEK_KARTI'na yazar, ardından embedding'ini hesaplar.

    Tekrarlanabilir: aynı `oturum_id` ikinci kez onaylanırsa (çift tıklama,
    embedding hatası sonrası yeniden deneme) yeni kart açılmaz, mevcut kart
    200 ile döner — embedding'i eksikse bu sırada yeniden denenir.
    """
    config = {"configurable": {"thread_id": str(istek.oturum_id)}}
    mevcut = await _grafik(request).aget_state(config)
    if not mevcut.values:
        raise HTTPException(status_code=404, detail="Sohbet oturumu bulunamadı")

    onceki = await _oturumun_karti(oturum, istek.oturum_id)
    if onceki is not None:
        yanit.status_code = 200
        return await _mevcut_karti_don(oturum, onceki)

    if not mevcut.values.get("taslak_hazir"):
        raise HTTPException(status_code=409, detail="Taslak henüz hazır değil")

    taslak = istek.duzeltilmis_taslak or KartTaslagi(**mevcut.values["taslak"])
    if not taslak.rol_alani or not taslak.deneyim_seviyesi:
        raise HTTPException(status_code=422, detail="Taslakta rol ve deneyim seviyesi zorunlu")

    kullanici = await _kullaniciyi_bul_veya_olustur(oturum, istek)

    kart = YetenekKarti(
        oturum_id=istek.oturum_id,
        kullanici_id=kullanici.id,
        rol_alani=taslak.rol_alani,
        deneyim_seviyesi=taslak.deneyim_seviyesi,
        sektor_ilgi_alani=taslak.sektor_ilgi_alani,
        araclar_teknolojiler=taslak.araclar_teknolojiler,
        # Kanıt linki olmayan bir çıktı varsa kart "kanıt bekleyen" sayılır;
        # Doğrulama Ajanı bunları Faz 2'de ele alacak.
        kanit_bekleyen=any(not c.kanit_linki for c in taslak.somut_ciktilar),
        somut_ciktilar=[
            SomutCikti(baslik=c.baslik, aciklama=c.aciklama, kanit_linki=c.kanit_linki)
            for c in taslak.somut_ciktilar
        ],
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
        return await _mevcut_karti_don(oturum, onceki)

    # Kart kaydedildikten SONRA embedding (docs/matching-algorithm.md § 1-2).
    # Voyage'a ulaşılamazsa kart kaybolmaz: embedding NULL kalır, yanıtta
    # `embedding_var: false` döner ve arayüz yeniden hesaplatmayı önerir.
    await embedding_hesapla(oturum, kart)

    return await kart_yaniti(oturum, kart.id)


async def _oturumun_karti(oturum: AsyncSession, oturum_id: uuid.UUID) -> YetenekKarti | None:
    return await oturum.scalar(
        select(YetenekKarti)
        .options(selectinload(YetenekKarti.somut_ciktilar))
        .where(YetenekKarti.oturum_id == oturum_id)
    )


async def _mevcut_karti_don(oturum: AsyncSession, kart: YetenekKarti) -> YetenekKartiYaniti:
    """Daha önce onaylanmış kartı döner; embedding'i eksikse bir kez daha dener."""
    if kart.embedding is None:
        await embedding_hesapla(oturum, kart)
    return await kart_yaniti(oturum, kart.id)


async def _kullaniciyi_bul_veya_olustur(oturum: AsyncSession, istek: KartOnaylaIstegi) -> Kullanici:
    girdi = istek.kullanici
    kullanici = await oturum.scalar(select(Kullanici).where(Kullanici.email == str(girdi.email)))
    if kullanici is None:
        kullanici = Kullanici(
            ad=girdi.ad,
            email=str(girdi.email),
            sehir=sehir_kanonik(girdi.sehir),
            calisma_modelleri=calisma_modeli.temizle(girdi.calisma_modelleri),
            musaitlik=girdi.musaitlik,
        )
        oturum.add(kullanici)
        await oturum.flush()
    return kullanici
