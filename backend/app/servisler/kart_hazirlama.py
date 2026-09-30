"""Yetenek kartını eşleştirmeye hazırlama (docs/plans/genc-akisi.md § 5.5, § 6.4).

Kart onaylanınca ya da değişince yanıttan sonra arka planda çalışır:

  1. Embedding: yoksa (ya da kart değiştiyse) hesaplanır.
  2. Doğrulama: linki olan ve puanı olmayan iş kalemleri puanlanır. Linksiz
     kalem puanlanmaz, "doğrulanmamış" nötr durumda kalır (plan § 0, karar 7).
  3. Yeniden eşleştirme: kartla konu olarak ilgili (benzerlik alt sınırını
     geçen) açık ihtiyaç kartları ve kartın hâlâ `onerildi` önerisi olan
     ihtiyaç kartları için mevcut pipeline çalışır. Bu, "sonradan gelen genç
     mevcut ihtiyaçlarla eşleşmiyor" açığını kapatır. Yeni bir eşleştirme
     mekanizması yok: pipeline ihtiyaç kartı başına aynı pipeline.

Sıra önemli: puan önce yazılır ki eşleşme skoru doğrulama bonusunu içersin.

İdempotentlik (aynı kart için iş iki kez sıraya girerse):
  - İş başında kartın versiyonu beklenenden büyükse iş çıkar; daha yeni bir iş
    zaten sırada.
  - İş kalemi satırı kilitlenerek okunur ve puanı varsa atlanır: ikinci iş
    birincinin commit'ini bekler, puanı hazır bulur, LLM'i ikinci kez çağırmaz.
  - Pipeline ihtiyaç kartı başına danışma kilidi ve ON CONFLICT ile çalışıyor;
    eşleşme satırı ve "yeni öneri" bildirimi çiftlenmez.

Zamanlayıcı yok (CLAUDE.md): bu da bir isteğin tetiklediği iş. Hata yutulur:
genç kartını zaten onayladı, arka plandaki hesap yüzünden bir şey kaybetmemeli.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.dogrulama import otomatik_puanlanir_mi
from app.agents.eslestirme import BENZERLIK_ALT_SINIRI, DURUM_ONERILDI
from app.api.yetenek_kartlari import embedding_hesapla
from app.core.ilan import ARANAN_GENC
from app.core.llm import HizSinirHatasi, ModelMesgulHatasi
from app.db.session import get_sessionmaker
from app.models.eslesme import Eslesme
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler import eslestirme as eslestirme_servisi
from app.servisler.dogrulama import ciktiyi_puanla

logger = logging.getLogger("zemin360.kart_hazirlama")

IHTIYAC_ACIK = "acik"


async def karti_hazirla(kart_id: uuid.UUID, versiyon: int, embedding_yenile: bool = False) -> None:
    """Arka plan işi: kendi oturumunu açar, hatayı yutar (bkz. modül notu)."""
    async with get_sessionmaker()() as oturum:
        try:
            await karti_hazirla_oturumla(
                oturum, kart_id, versiyon, embedding_yenile=embedding_yenile
            )
        except Exception:
            logger.exception("Kart hazırlama başarısız (%s)", kart_id)


async def karti_hazirla_oturumla(
    oturum: AsyncSession, kart_id: uuid.UUID, versiyon: int, *, embedding_yenile: bool = False
) -> None:
    kart = await _karti_oku(oturum, kart_id)
    if kart is None or kart.versiyon > versiyon:
        # Silinmiş ya da daha yeni bir hazırlama sırada.
        return

    if kart.embedding is None or embedding_yenile:
        if not await embedding_hesapla(oturum, kart):
            # Embedding'siz kart eşleştirmeye giremez; genç "eşleştirmeye
            # hazırla" ile yeniden deneyebilir (mevcut yol).
            return

    for cikti_id in [c.id for c in kart.somut_ciktilar]:
        await _ciktiyi_puanla_bir_kez(oturum, cikti_id)

    await yetenek_kartini_eslestir(oturum, kart_id)


async def _karti_oku(oturum: AsyncSession, kart_id: uuid.UUID) -> YetenekKarti | None:
    return await oturum.scalar(
        select(YetenekKarti)
        .options(selectinload(YetenekKarti.somut_ciktilar))
        .where(YetenekKarti.id == kart_id)
        .execution_options(populate_existing=True)
    )


async def _ciktiyi_puanla_bir_kez(oturum: AsyncSession, cikti_id: uuid.UUID) -> None:
    """Kalemi kilitleyerek okur; puanlanacaksa puanlar ve hemen commit eder.

    LLM hız sınırında ya da arızasında kalem puansız kalır: genç kart
    sayfasından "değerlendir"e basabilir, bir sonraki hazırlama yine dener.
    """
    cikti = await oturum.scalar(
        select(SomutCikti)
        # Referanslar: sıfırdan yazılan göstergede güncel yanıtlar sayılıyor.
        .options(selectinload(SomutCikti.guven_skoru), selectinload(SomutCikti.referans_istekleri))
        .where(SomutCikti.id == cikti_id)
        .with_for_update(of=SomutCikti)
        .execution_options(populate_existing=True)
    )
    if cikti is None or not otomatik_puanlanir_mi(cikti.kanit_linki, cikti.guven_skoru is not None):
        await oturum.rollback()  # kilidi bırak
        return
    try:
        await ciktiyi_puanla(cikti)
    except (HizSinirHatasi, ModelMesgulHatasi):
        logger.info("İş kalemi şimdi puanlanamadı, puansız kaldı (%s)", cikti_id)
        await oturum.rollback()
        return
    except Exception:
        # Bir kalemin beklenmeyen hatası diğer kalemleri ve eşleştirmeyi durdurmasın.
        logger.exception("İş kalemi puanlanırken hata; puansız kaldı (%s)", cikti_id)
        await oturum.rollback()
        return
    await oturum.commit()


async def ilgili_ihtiyac_kartlari(oturum: AsyncSession, kart_id: uuid.UUID) -> list[uuid.UUID]:
    """Bu kart için pipeline'ı çalıştırılacak ihtiyaç kartları.

    (a) Açık, embedding'i olan ve kartla benzerliği alt sınırı geçenler:
        kart oralara yeni öneri olabilir.
    (b) Kartın hâlâ `onerildi` önerisi olanlar: kart artık uymuyorsa öneri
        pipeline'ın mevcut kuralıyla temizlensin.
    Eşik ve sert filtreler pipeline'ın işi; burada yalnızca aday daraltılıyor.
    """
    kart_vektoru = select(YetenekKarti.embedding).where(YetenekKarti.id == kart_id)
    uzaklik = IhtiyacKarti.embedding.cosine_distance(kart_vektoru.scalar_subquery())
    onerildigi = select(Eslesme.ihtiyac_karti_id).where(
        Eslesme.yetenek_karti_id == kart_id, Eslesme.durum == DURUM_ONERILDI
    )
    satirlar = await oturum.scalars(
        select(IhtiyacKarti.id).where(
            IhtiyacKarti.embedding.isnot(None),
            IhtiyacKarti.durum == IHTIYAC_ACIK,
            # Yetenek kartı yalnızca genç ilanlarına aday (firma-akisi § 4).
            IhtiyacKarti.aranan == ARANAN_GENC,
            or_(uzaklik <= 1.0 - BENZERLIK_ALT_SINIRI, IhtiyacKarti.id.in_(onerildigi)),
        )
    )
    return list(satirlar)


async def yetenek_kartini_eslestir(oturum: AsyncSession, kart_id: uuid.UUID) -> int:
    """İlgili her ihtiyaç kartı için mevcut pipeline'ı çalıştırır. Döner: kaç ihtiyaç."""
    ihtiyac_idleri = await ilgili_ihtiyac_kartlari(oturum, kart_id)
    for ihtiyac_id in ihtiyac_idleri:
        ihtiyac = await oturum.get(IhtiyacKarti, ihtiyac_id)
        if ihtiyac is None:
            continue
        try:
            await eslestirme_servisi.pipeline_calistir(oturum, ihtiyac)
        except HTTPException as hata:
            logger.info("Eşleştirme atlandı (%s): %s", ihtiyac_id, hata.detail)
    return len(ihtiyac_idleri)
