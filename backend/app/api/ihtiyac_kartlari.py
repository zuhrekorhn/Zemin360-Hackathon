"""İhtiyaç kartı okuma, düzenleme, kapatma ve embedding uç noktaları.

Gizlilik: yanıt kurumun iletişim e-postasını İÇERMEZ (şema o alanı hiç
taşımıyor). Eşleştirme Ajanı da bu görünümü okuyor.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.tanimlama import ZORUNLU_ALANLAR
from app.api.kimlik import bulunamadi, mevcut_hesap, rol_gerekli
from app.core.alan_adlari import IHTIYAC_ALAN_ADLARI, bos_alan_mesaji
from app.core.basari_olcutu import olcum_belirlenecek
from app.core.firma_dogrulama import DOGRULANDI
from app.db.session import get_session
from app.models.hesap import ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.schemas.tanimlama import (
    IhtiyacKartiKapatIstegi,
    IhtiyacKartiYaniti,
    IhtiyacTaslagiGirdisi,
    KurumYaniti,
)
from app.servisler.embedding import EMBEDDING_HATA_MESAJI, embedding_hesapla
from app.servisler.eslestirme import eslestirmeyi_arka_planda_calistir, ihtiyac_kilidi
from app.servisler.ilan_duzenleme import duzenleme_engeli, ilan_eslesmeleri, ilani_duzenle
from app.servisler.ilgi import IHTIYAC_KAPANDI, ihtiyaci_kapat
from app.servisler.sahiplik import (
    girvak_mi,
    ihtiyac_kartini_gorebilir_mi,
    ihtiyac_kartinin_sahibi_mi,
)

router = APIRouter(tags=["ihtiyac-kartlari"])

KART_BULUNAMADI = "İhtiyaç kartı bulunamadı"


async def kart_yaniti(oturum: AsyncSession, kart_id: uuid.UUID) -> IhtiyacKartiYaniti:
    """Kartı kurumuyla okuyup dışarıya açılan şemaya çevirir."""
    kart = await oturum.scalar(
        select(IhtiyacKarti)
        .options(selectinload(IhtiyacKarti.kurum))
        .where(IhtiyacKarti.id == kart_id)
    )
    if kart is None:
        raise bulunamadi(KART_BULUNAMADI)
    return IhtiyacKartiYaniti(
        id=kart.id,
        problem_tanimi=kart.problem_tanimi,
        basari_kriteri=kart.basari_kriteri,
        basari_olcutu=kart.basari_olcutu,
        olcum_belirlenecek=olcum_belirlenecek(kart.basari_olcutu),
        kisitlar=kart.kisitlar,
        sehir_tercihi=kart.sehir_tercihi,
        calisma_modeli=kart.calisma_modeli,
        musaitlik_tercihi=kart.musaitlik_tercihi,
        embedding_var=kart.embedding is not None,
        durum=kart.durum,
        aranan=kart.aranan,
        aranan_firma_turleri=list(kart.aranan_firma_turleri),
        isbirligi_turu=kart.isbirligi_turu,
        kurum=KurumYaniti(
            id=kart.kurum.id,
            ad=kart.kurum.ad,
            dogrulandi=kart.kurum.dogrulama_durumu == DOGRULANDI,
            sektor=kart.kurum.sektor,
            sehir=kart.kurum.sehir,
        ),
    )


@router.get("/ihtiyac-kartlari/{kart_id}", response_model=IhtiyacKartiYaniti)
async def ihtiyac_karti_getir(
    kart_id: uuid.UUID,
    hesap: Hesap = Depends(mevcut_hesap),
    oturum: AsyncSession = Depends(get_session),
) -> IhtiyacKartiYaniti:
    """Kurum kendi kartını, genç kendisine ilgi gösterilmiş ihtiyacı, GİRVAK hepsini görür."""
    kart = await oturum.get(IhtiyacKarti, kart_id)
    if kart is None or not await ihtiyac_kartini_gorebilir_mi(oturum, hesap, kart):
        raise bulunamadi(KART_BULUNAMADI)
    return await kart_yaniti(oturum, kart_id)


@router.post("/ihtiyac-kartlari/{kart_id}/embedding", response_model=IhtiyacKartiYaniti)
async def ihtiyac_karti_embedding(
    kart_id: uuid.UUID,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(mevcut_hesap),
    oturum: AsyncSession = Depends(get_session),
) -> IhtiyacKartiYaniti:
    """Embedding'i yeniden hesaplar; başarılıysa eşleştirmeyi de başlatır.

    Onayda Voyage'a ulaşılamadıysa eşleştirme de hiç başlamamıştı — kart
    ancak embedding'i olunca aday bulabiliyor.
    """
    kart = await oturum.scalar(select(IhtiyacKarti).where(IhtiyacKarti.id == kart_id))
    if kart is None or not (girvak_mi(hesap) or ihtiyac_kartinin_sahibi_mi(hesap, kart)):
        raise bulunamadi(KART_BULUNAMADI)
    if not await embedding_hesapla(oturum, kart):
        raise HTTPException(status_code=503, detail=EMBEDDING_HATA_MESAJI)
    arka_plan.add_task(eslestirmeyi_arka_planda_calistir, kart.id)
    return await kart_yaniti(oturum, kart.id)


@router.post("/ihtiyac-kartlari/{kart_id}/kapat", response_model=IhtiyacKartiYaniti)
async def ihtiyac_karti_kapat(
    kart_id: uuid.UUID,
    istek: IhtiyacKartiKapatIstegi,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> IhtiyacKartiYaniti:
    """Firma ilanını kapatır (docs/kararlar.md F7).

    Bekleyen ilgiler "kapandı" olur ve nötr bildirim gider (app/servisler/ilgi.py).
    Kapanan ilan tekrar açılmaz; ikinci istek 200 döner ve yan etkisizdir (ilk
    neden korunur). Başkasının ilanı 404. Pipeline ile aynı kilidi alır:
    çalışan bir eşleştirme bitmeden kapatma yazılmaz.
    """
    await ihtiyac_kilidi(oturum, kart_id)
    kart = await oturum.scalar(
        select(IhtiyacKarti)
        .where(IhtiyacKarti.id == kart_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if kart is None or not ihtiyac_kartinin_sahibi_mi(hesap, kart):
        raise bulunamadi(KART_BULUNAMADI)
    if kart.durum != IHTIYAC_KAPANDI:
        await ihtiyaci_kapat(oturum, kart, istek.neden)
    await oturum.commit()
    return await kart_yaniti(oturum, kart.id)


@router.patch("/ihtiyac-kartlari/{kart_id}", response_model=IhtiyacKartiYaniti)
async def ihtiyac_karti_duzenle(
    kart_id: uuid.UUID,
    istek: IhtiyacTaslagiGirdisi,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> IhtiyacKartiYaniti:
    """Firma açık ilanını yerinde düzenler (docs/kararlar.md D1).

    Onay formundaki gövdenin tamamı gelir; `aranan` (kapı) değişmez. Kapalı
    ilan ya da iş birliği başlamış ilan 409. Değişmeyen düzenleme yan etkisiz.
    Değişince eski gerekçeler sıfırlanır, ilgilenmiş aday bildirim alır,
    embedding yeniden hesaplanır ve eşleştirme yanıttan sonra yeniden çalışır;
    firmanın kararları ve gencin ilgisi korunur. Embedding hesaplanamazsa
    düzenleme yine kaydedilir (`embedding_var: false`). Pipeline ile aynı kilit.
    """
    if bos := [alan for alan in ZORUNLU_ALANLAR if not getattr(istek, alan)]:
        raise HTTPException(
            status_code=422, detail=bos_alan_mesaji(bos, IHTIYAC_ALAN_ADLARI, siz=True)
        )
    await ihtiyac_kilidi(oturum, kart_id)
    kart = await oturum.scalar(
        select(IhtiyacKarti)
        .where(IhtiyacKarti.id == kart_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if kart is None or not ihtiyac_kartinin_sahibi_mi(hesap, kart):
        raise bulunamadi(KART_BULUNAMADI)
    eslesmeler = await ilan_eslesmeleri(oturum, kart)
    if engel := duzenleme_engeli(kart, eslesmeler):
        raise HTTPException(status_code=409, detail=engel)
    if not ilani_duzenle(oturum, kart, eslesmeler, istek):
        await oturum.rollback()  # kilidi bırak
        return await kart_yaniti(oturum, kart_id)
    await oturum.commit()
    if await embedding_hesapla(oturum, kart):
        arka_plan.add_task(eslestirmeyi_arka_planda_calistir, kart.id)
    return await kart_yaniti(oturum, kart_id)
