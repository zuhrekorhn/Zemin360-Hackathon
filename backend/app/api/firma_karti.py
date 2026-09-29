"""Firma kartı uçları (docs/plans/firma-akisi.md § 0 kararlar 3, 9, 10; § 5).

Kart sohbetle oluşur (`/sohbet/baslat`, `/sohbet/cevap`, `/onayla`; Keşif ve
Tanımlama ile aynı motor ve aynı desen), sonra formla düzenlenir. Yalnızca
firma, yalnızca kendi kartı: kart token'daki firmanın kartı, başkasının kartı
diye bir yol yok. Genç ve GİRVAK 403, token yok 401.

Düzenleme, yetenek kartındaki gibi: satır kilitli okunur (aynı anda iki
düzenleme versiyonu ezmesin), gerçek değişiklikte versiyon artar ve firmanın
ne yaptığını anlatan alanlar değiştiyse kart yanıttan sonra yeniden hazırlanır.
Aynı değerle gelen düzenleme hiçbir şeyi tetiklemez.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.firma_karti import profil_baglami
from app.agents.sohbet_motoru import HizSinirHatasi, kullanici_mesaji
from app.api.kimlik import rol_gerekli
from app.api.sahiplik import bulunamadi, sohbet_baslangici, sohbetin_sahibi_mi
from app.core.firma_karti import ZORUNLU_ALANLAR
from app.core.hatalar import HIZ_SINIRI_MESAJI
from app.db.session import get_session
from app.models.firma_karti import FirmaKarti
from app.models.hesap import ROL_KURUM, Hesap
from app.schemas.firma_karti import (
    FirmaKartiGirdisi,
    FirmaKartiGuncelleme,
    FirmaKartiOnaylaIstegi,
    FirmaKartiSohbetYaniti,
    FirmaKartiTaslagi,
    FirmaKartiYaniti,
)
from app.schemas.sohbet import SohbetBaslatIstegi, SohbetCevapIstegi
from app.servisler import firma_karti as servis

router = APIRouter(prefix="/kurum/kart", tags=["firma-karti"])

KART_YOK = "Firma kartınız henüz yok."
KART_VAR = "Firma kartınız zaten var; kart sayfasından düzenleyebilirsiniz."
OTURUM_YOK = "Sohbet oturumu bulunamadı"
TASLAK_HAZIR = "Taslak hazır; sıradaki adım onay"
TASLAK_HAZIR_DEGIL = "Taslak henüz hazır değil"
TASLAK_EKSIK = "Kartta firmanın ne yaptığı ve en az bir yetkinlik olmalı."


def kart_yaniti(kart: FirmaKarti) -> FirmaKartiYaniti:
    """`kart` kurumuyla yüklenmiş olmalı."""
    return FirmaKartiYaniti(
        id=kart.id,
        kurum_id=kart.kurum_id,
        firma_adi=kart.kurum.ad,
        ne_yapiyoruz=kart.ne_yapiyoruz,
        yetkinlikler=list(kart.yetkinlikler),
        onceki_isler=kart.onceki_isler,
        aranan_isbirligi=kart.aranan_isbirligi,
        isbirligi_turleri=list(kart.isbirligi_turleri),
        versiyon=kart.versiyon,
        embedding_var=kart.embedding is not None,
        olusturma_tarihi=kart.olusturma_tarihi,
    )


@router.get("", response_model=FirmaKartiYaniti | None)
async def kartim(
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> FirmaKartiYaniti | None:
    """Firmanın kartı; yoksa `null` (kart isteğe bağlı, karar 9: hata değil)."""
    kart = await servis.kurumun_karti(oturum, hesap.kurum.id)
    return kart_yaniti(kart) if kart else None


@router.patch("", response_model=FirmaKartiYaniti)
async def karti_duzenle(
    istek: FirmaKartiGuncelleme,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> FirmaKartiYaniti:
    gonderilenler = {alan: getattr(istek, alan) for alan in istek.model_fields_set}
    bosalanlar = sorted(a for a in ZORUNLU_ALANLAR if a in gonderilenler and not gonderilenler[a])
    if bosalanlar:
        raise HTTPException(
            status_code=422, detail=f"Bu alanlar boş bırakılamaz: {', '.join(bosalanlar)}"
        )
    # Kimlik işlem başında alınır: geri almadan sonra `hesap.kurum`un süresi dolar.
    kurum_id = hesap.kurum.id
    kart = await servis.kurumun_karti(oturum, kurum_id, kilitle=True)
    if kart is None:
        raise bulunamadi(KART_YOK)

    degisenler = servis.kart_alanlarini_yaz(kart, gonderilenler)
    if not degisenler:
        await oturum.rollback()  # kilidi bırak
        kart = await servis.kurumun_karti(oturum, kurum_id)
        return kart_yaniti(kart)

    kart.versiyon += 1
    yenile = servis.embedding_yenilenmeli_mi(degisenler)
    if yenile:
        # Eski vektör artık kartı temsil etmiyor: hazırlanana kadar eşleşmeye girmesin.
        kart.embedding = None
    kart_id, versiyon = kart.id, kart.versiyon
    await oturum.commit()
    if yenile:
        arka_plan.add_task(servis.firma_kartini_hazirla, kart_id, versiyon)
    kart = await servis.kurumun_karti(oturum, kurum_id)
    return kart_yaniti(kart)


# --- Sohbet (docs/plans/firma-akisi.md § 5) ----------------------------------------------


def _grafik(request: Request):
    grafik = getattr(request.app.state, "firma_karti_grafigi", None)
    if grafik is None:
        raise HTTPException(status_code=503, detail="Kart sohbeti şu an hazır değil")
    return grafik


def _sohbet_yaniti(oturum_id: uuid.UUID, durum: dict) -> FirmaKartiSohbetYaniti:
    return FirmaKartiSohbetYaniti(
        oturum_id=oturum_id,
        soru=durum.get("sonraki_soru"),
        taslak=FirmaKartiTaslagi(**(durum.get("taslak") or {})),
        taslak_hazir=bool(durum.get("taslak_hazir")),
    )


@router.post("/sohbet/baslat", response_model=FirmaKartiSohbetYaniti)
async def sohbet_baslat(
    _: SohbetBaslatIstegi,
    request: Request,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> FirmaKartiSohbetYaniti:
    """Kartı olan firma yeni sohbet açamaz (409): kart formla düzenlenir."""
    if await servis.kurumun_karti(oturum, hesap.kurum.id) is not None:
        raise HTTPException(status_code=409, detail=KART_VAR)
    oturum_id = uuid.uuid4()
    baslangic = {**sohbet_baslangici(hesap), "profil_baglami": profil_baglami(hesap.kurum)}
    durum = await _grafik(request).ainvoke(
        baslangic, config={"configurable": {"thread_id": str(oturum_id)}}
    )
    return _sohbet_yaniti(oturum_id, durum)


@router.post("/sohbet/cevap", response_model=FirmaKartiSohbetYaniti)
async def sohbet_cevap(
    istek: SohbetCevapIstegi, request: Request, hesap: Hesap = Depends(rol_gerekli(ROL_KURUM))
) -> FirmaKartiSohbetYaniti:
    config = {"configurable": {"thread_id": str(istek.oturum_id)}}
    grafik = _grafik(request)
    mevcut = await grafik.aget_state(config)
    if not mevcut.values or not sohbetin_sahibi_mi(mevcut.values, hesap):
        raise HTTPException(status_code=404, detail=OTURUM_YOK)
    if mevcut.values.get("taslak_hazir"):
        raise HTTPException(status_code=409, detail=TASLAK_HAZIR)
    try:
        durum = await grafik.ainvoke({"mesajlar": [kullanici_mesaji(istek.cevap)]}, config=config)
    except HizSinirHatasi as hata:
        raise HTTPException(
            status_code=429, detail=f"{HIZ_SINIRI_MESAJI} Sohbetiniz kayıtlı."
        ) from hata
    return _sohbet_yaniti(istek.oturum_id, durum)


@router.post("/onayla", response_model=FirmaKartiYaniti, status_code=201)
async def onayla(
    istek: FirmaKartiOnaylaIstegi,
    request: Request,
    arka_plan: BackgroundTasks,
    yanit: Response,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> FirmaKartiYaniti:
    """Taslağı `firma_karti`'na yazar; kart yanıttan sonra hazırlanır.

    Tekrarlanabilir: aynı `oturum_id` ikinci kez onaylanırsa mevcut kart 200
    ile döner. Firmanın başka bir kartı varsa 409 (firma başına bir kart).
    """
    config = {"configurable": {"thread_id": str(istek.oturum_id)}}
    mevcut = await _grafik(request).aget_state(config)
    if not mevcut.values or not sohbetin_sahibi_mi(mevcut.values, hesap):
        raise HTTPException(status_code=404, detail=OTURUM_YOK)

    kurum_id = hesap.kurum.id
    onceki = await _oturumun_karti(oturum, istek.oturum_id)
    if onceki is not None:
        yanit.status_code = 200
        return kart_yaniti(onceki)
    if await servis.kurumun_karti(oturum, kurum_id) is not None:
        raise HTTPException(status_code=409, detail=KART_VAR)
    if not mevcut.values.get("taslak_hazir"):
        raise HTTPException(status_code=409, detail=TASLAK_HAZIR_DEGIL)

    girdi = istek.duzeltilmis_taslak
    if girdi is None:
        try:
            girdi = FirmaKartiGirdisi(**(mevcut.values.get("taslak") or {}))
        except ValidationError as hata:
            raise HTTPException(status_code=422, detail=TASLAK_EKSIK) from hata

    try:
        kart = await servis.karti_olustur(
            oturum, kurum_id, girdi.model_dump(), oturum_id=istek.oturum_id
        )
        kart_id = kart.id
        await oturum.commit()
    except IntegrityError:
        # Eşzamanlı ikinci onay: diğer istek kartı yazdı (oturum ya da firma tekil).
        await oturum.rollback()
        onceki = await _oturumun_karti(oturum, istek.oturum_id)
        if onceki is None:
            raise HTTPException(status_code=409, detail=KART_VAR) from None
        yanit.status_code = 200
        return kart_yaniti(onceki)

    arka_plan.add_task(servis.firma_kartini_hazirla, kart_id, 1)
    return kart_yaniti(await servis.kurumun_karti(oturum, kurum_id))


async def _oturumun_karti(oturum: AsyncSession, oturum_id: uuid.UUID) -> FirmaKarti | None:
    return await oturum.scalar(
        select(FirmaKarti)
        .options(selectinload(FirmaKarti.kurum))
        .where(FirmaKarti.oturum_id == oturum_id)
    )
