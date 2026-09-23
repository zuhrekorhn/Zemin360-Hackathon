"""Keşif Ajanı uç noktaları (docs/api-contracts.md § Keşif).

Sohbet durumu LangGraph'ın Postgres checkpointer'ında, `oturum_id` de
thread_id olarak tutulur — uygulama tarafında ayrı bir oturum tablosu yok.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.kesif import HizSinirHatasi, kullanici_mesaji
from app.api.yetenek_kartlari import kart_yaniti
from app.core.embeddings import embedding_uret, yetenek_temsil_metni
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
    oturum: AsyncSession = Depends(get_session),
) -> YetenekKartiYaniti:
    """Onaylanan taslağı YETENEK_KARTI'na yazar, ardından embedding'ini hesaplar."""
    config = {"configurable": {"thread_id": str(istek.oturum_id)}}
    mevcut = await _grafik(request).aget_state(config)
    if not mevcut.values:
        raise HTTPException(status_code=404, detail="Sohbet oturumu bulunamadı")
    if not mevcut.values.get("taslak_hazir"):
        raise HTTPException(status_code=409, detail="Taslak henüz hazır değil")

    taslak = istek.duzeltilmis_taslak or KartTaslagi(**mevcut.values["taslak"])
    if not taslak.rol_alani or not taslak.deneyim_seviyesi:
        raise HTTPException(status_code=422, detail="Taslakta rol ve deneyim seviyesi zorunlu")

    kullanici = await _kullaniciyi_bul_veya_olustur(oturum, istek)

    kart = YetenekKarti(
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
    await oturum.commit()

    # Kart kaydedildikten SONRA embedding (docs/matching-algorithm.md § 1-2).
    # Voyage'a ulaşılamazsa kart kaybolmasın: kayıt durur, embedding NULL kalır
    # ve kart eşleştirmeye girmez.
    metin = yetenek_temsil_metni(
        rol_alani=kart.rol_alani,
        deneyim_seviyesi=kart.deneyim_seviyesi,
        sektor_ilgi_alani=kart.sektor_ilgi_alani,
        araclar_teknolojiler=kart.araclar_teknolojiler,
        somut_ciktilar=[(c.baslik, c.aciklama) for c in taslak.somut_ciktilar],
    )
    kart.embedding = await embedding_uret(metin, girdi_turu="document")
    await oturum.commit()

    return await kart_yaniti(oturum, kart.id)


async def _kullaniciyi_bul_veya_olustur(oturum: AsyncSession, istek: KartOnaylaIstegi) -> Kullanici:
    girdi = istek.kullanici
    kullanici = await oturum.scalar(select(Kullanici).where(Kullanici.email == str(girdi.email)))
    if kullanici is None:
        kullanici = Kullanici(
            ad=girdi.ad,
            email=str(girdi.email),
            sehir=girdi.sehir,
            musaitlik=girdi.musaitlik,
        )
        oturum.add(kullanici)
        await oturum.flush()
    return kullanici
