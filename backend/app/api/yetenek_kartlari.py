"""Yetenek kartı okuma ve embedding uç noktaları.

Gizlilik (docs/agent-specs.md § 1.5): bu yanıt kullanıcının e-postasını ve
diğer iletişim bilgilerini İÇERMEZ — kart görünür, iletişim iki taraf da
onaylayınca açılır. Şema (app/schemas/kesif.py) bu alanları hiç taşımıyor,
yani yanlışlıkla sızdırmak için şemayı değiştirmek gerekir.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.eslestirme import tamamlanan_pilot_sayilari
from app.api.kimlik import mevcut_hesap
from app.api.sahiplik import (
    bulunamadi,
    girvak_mi,
    yetenek_kartini_gorebilir_mi,
    yetenek_kartinin_sahibi_mi,
)
from app.core.embeddings import EmbeddingHatasi, embedding_uret, yetenek_temsil_metni
from app.db.session import get_session
from app.models.hesap import Hesap
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.kesif import YetenekKartiYaniti

logger = logging.getLogger("zemin360.embedding")

router = APIRouter(tags=["yetenek-kartlari"])

KART_BULUNAMADI = "Yetenek kartı bulunamadı"

EMBEDDING_HATA_MESAJI = (
    "Kart kayıtlı, ama eşleştirmeye hazırlanamadı (vektör servisine ulaşılamadı). "
    "Biraz sonra tekrar dene."
)


async def kart_yaniti(oturum: AsyncSession, kart_id: uuid.UUID) -> YetenekKartiYaniti:
    """Kartı ilişkileriyle okuyup dışarıya açılan şemaya çevirir.

    Keşif Ajanı da onay sonrası yanıtı bunun üzerinden döner — iki uç noktanın
    aynı kartı farklı alanlarla göstermemesi için tek yer.
    """
    kart = await oturum.scalar(
        select(YetenekKarti)
        .options(
            selectinload(YetenekKarti.somut_ciktilar).selectinload(SomutCikti.guven_skoru),
            selectinload(YetenekKarti.kullanici),
        )
        .where(YetenekKarti.id == kart_id)
    )
    if kart is None:
        raise bulunamadi(KART_BULUNAMADI)
    return YetenekKartiYaniti(
        id=kart.id,
        genc_adi=kart.kullanici.ad,
        rol_alani=kart.rol_alani,
        deneyim_seviyesi=kart.deneyim_seviyesi,
        sektor_ilgi_alani=kart.sektor_ilgi_alani,
        araclar_teknolojiler=kart.araclar_teknolojiler,
        kanit_bekleyen=kart.kanit_bekleyen,
        versiyon=kart.versiyon,
        embedding_var=kart.embedding is not None,
        somut_ciktilar=kart.somut_ciktilar,
        tamamlanan_pilot=(await tamamlanan_pilot_sayilari(oturum, [kart.id])).get(kart.id, 0),
    )


async def embedding_hesapla(oturum: AsyncSession, kart: YetenekKarti) -> bool:
    """Kartın embedding'ini hesaplayıp kaydeder (docs/matching-algorithm.md § 1-2).

    Voyage'a ulaşılamazsa hata fırlatmaz, False döner: kart zaten kayıtlı ve
    kaybolmamalı. Embedding NULL kalan kart eşleştirmeye girmez; arayüz bunu
    söyleyip yeniden hesaplatma butonu gösteriyor.

    `kart.somut_ciktilar` yüklenmiş olmalı (temsil metni onlardan kuruluyor).
    """
    metin = yetenek_temsil_metni(
        rol_alani=kart.rol_alani,
        deneyim_seviyesi=kart.deneyim_seviyesi,
        sektor_ilgi_alani=kart.sektor_ilgi_alani,
        araclar_teknolojiler=kart.araclar_teknolojiler,
        somut_ciktilar=[(c.baslik, c.aciklama) for c in kart.somut_ciktilar],
    )
    try:
        kart.embedding = await embedding_uret(metin, girdi_turu="document")
    except EmbeddingHatasi:
        logger.warning("Yetenek kartı embedding'i hesaplanamadı (%s)", kart.id, exc_info=True)
        return False
    await oturum.commit()
    return True


@router.get("/yetenek-kartlari/{kart_id}", response_model=YetenekKartiYaniti)
async def yetenek_karti_getir(
    kart_id: uuid.UUID,
    hesap: Hesap = Depends(mevcut_hesap),
    oturum: AsyncSession = Depends(get_session),
) -> YetenekKartiYaniti:
    """Genç kendi kartını, kurum kendisine önerilmiş kartı, GİRVAK hepsini görür."""
    kart = await oturum.get(YetenekKarti, kart_id)
    if kart is None or not await yetenek_kartini_gorebilir_mi(oturum, hesap, kart):
        raise bulunamadi(KART_BULUNAMADI)
    return await kart_yaniti(oturum, kart_id)


@router.post("/yetenek-kartlari/{kart_id}/embedding", response_model=YetenekKartiYaniti)
async def yetenek_karti_embedding(
    kart_id: uuid.UUID,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(mevcut_hesap),
    oturum: AsyncSession = Depends(get_session),
) -> YetenekKartiYaniti:
    """Embedding'i yeniden hesaplar — onay sırasında Voyage'a ulaşılamadıysa.

    Kart zaten embedding'liyse de yeniden hesaplanır; zararsız ve temsil
    şablonu değiştiğinde tek tek tazelemenin yolu bu. Başarılıysa kart
    hazırlanır (puanlama ve mevcut ihtiyaçlarla eşleştirme): onayda embedding
    hesaplanamamışsa kart eşleştirmeye ancak şimdi girebiliyor.
    """
    kart = await oturum.scalar(
        select(YetenekKarti)
        .options(selectinload(YetenekKarti.somut_ciktilar))
        .where(YetenekKarti.id == kart_id)
    )
    # Yalnızca kartın sahibi (ve GİRVAK); kurum kartı görse de hesaplatamaz.
    if kart is None or not (girvak_mi(hesap) or yetenek_kartinin_sahibi_mi(hesap, kart)):
        raise bulunamadi(KART_BULUNAMADI)
    if not await embedding_hesapla(oturum, kart):
        raise HTTPException(status_code=503, detail=EMBEDDING_HATA_MESAJI)
    # kart_hazirlama bu modülü içe aktarıyor (embedding_hesapla); döngü olmasın.
    from app.servisler import kart_hazirlama

    arka_plan.add_task(kart_hazirlama.karti_hazirla, kart.id, kart.versiyon)
    return await kart_yaniti(oturum, kart.id)
