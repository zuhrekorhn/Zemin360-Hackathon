"""Yetenek kartı okuma ve embedding uç noktaları.

Gizlilik (docs/agent-specs.md § 1.5): bu yanıt kullanıcının e-postasını ve
diğer iletişim bilgilerini İÇERMEZ — kart görünür, iletişim iki taraf da
onaylayınca açılır. Şema (app/schemas/kesif.py) bu alanları hiç taşımıyor,
yani yanlışlıkla sızdırmak için şemayı değiştirmek gerekir.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.eslestirme import tamamlanan_pilot_sayilari
from app.api.kimlik import bulunamadi, mevcut_hesap
from app.core.dis_servisler.depo import DepoKapali
from app.db.session import get_session
from app.models.hesap import Hesap
from app.models.kanit_parcasi import KanitParcasi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.dogrulama import IndirmeAdresiYaniti
from app.schemas.kesif import YetenekKartiYaniti
from app.servisler import kart_hazirlama
from app.servisler.dogrulama import dosyalar
from app.servisler.dogrulama.parcalar import DOSYA_TURLERI
from app.servisler.embedding import EMBEDDING_HATA_MESAJI, embedding_hesapla
from app.servisler.sahiplik import (
    girvak_mi,
    yetenek_kartini_gorebilir_mi,
    yetenek_kartinin_sahibi_mi,
)

router = APIRouter(tags=["yetenek-kartlari"])

KART_BULUNAMADI = "Yetenek kartı bulunamadı"


async def kart_yaniti(oturum: AsyncSession, kart_id: uuid.UUID) -> YetenekKartiYaniti:
    """Kartı ilişkileriyle okuyup dışarıya açılan şemaya çevirir.

    Keşif Ajanı da onay sonrası yanıtı bunun üzerinden döner — iki uç noktanın
    aynı kartı farklı alanlarla göstermemesi için tek yer.
    """
    kart = await oturum.scalar(
        select(YetenekKarti)
        .options(
            selectinload(YetenekKarti.somut_ciktilar).selectinload(SomutCikti.guven_skoru),
            selectinload(YetenekKarti.somut_ciktilar).selectinload(SomutCikti.kanit_parcalari),
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
        sertifikalar=kart.sertifikalar,
        diller=kart.diller,
        kanit_bekleyen=kart.kanit_bekleyen,
        versiyon=kart.versiyon,
        embedding_var=kart.embedding is not None,
        somut_ciktilar=kart.somut_ciktilar,
        tamamlanan_pilot=(await tamamlanan_pilot_sayilari(oturum, [kart.id])).get(kart.id, 0),
    )


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
    yanit = await kart_yaniti(oturum, kart_id)
    if not (yetenek_kartinin_sahibi_mi(hesap, kart) or girvak_mi(hesap)):
        _kapali_dosyalari_gizle(yanit)
    return yanit


def _kapali_dosyalari_gizle(yanit: YetenekKartiYaniti) -> None:
    """Firma dosyanın sonucunu (seviye, gösterge) görür; gencin "firmalar görebilir"
    demediği dosyanın adını ve içerik bilgisini görmez (docs/dogrulama.md § 4.4)."""
    for cikti in yanit.somut_ciktilar:
        for kanit in cikti.kanitlar:
            if kanit.tur in DOSYA_TURLERI and not kanit.gorunur_firmaya:
                kanit.dosya_adi = None
                kanit.uretim_araci = None


@router.get(
    "/yetenek-kartlari/{kart_id}/kanit/{parca_id}/indir", response_model=IndirmeAdresiYaniti
)
async def kart_dosyasini_indir(
    kart_id: uuid.UUID,
    parca_id: uuid.UUID,
    hesap: Hesap = Depends(mevcut_hesap),
    oturum: AsyncSession = Depends(get_session),
) -> IndirmeAdresiYaniti:
    """Kart görünümünden dosya indirme. Firma yalnızca kartı görebiliyorsa ve genç
    dosyayı firmalara açtıysa; açılmamış dosya firmaya 404 (varlık sızmasın)."""
    kart = await oturum.get(YetenekKarti, kart_id)
    if kart is None or not await yetenek_kartini_gorebilir_mi(oturum, hesap, kart):
        raise bulunamadi(KART_BULUNAMADI)
    parca = await oturum.scalar(
        select(KanitParcasi)
        .join(SomutCikti, SomutCikti.id == KanitParcasi.somut_cikti_id)
        .where(KanitParcasi.id == parca_id, SomutCikti.yetenek_karti_id == kart_id)
    )
    tam_yetki = yetenek_kartinin_sahibi_mi(hesap, kart) or girvak_mi(hesap)
    if parca is None or not parca.dosya_anahtari or not (tam_yetki or parca.gorunur_firmaya):
        raise bulunamadi("Dosya bulunamadı.")
    try:
        return IndirmeAdresiYaniti(adres=await dosyalar.parca_indirme_adresi(parca))
    except DepoKapali as hata:
        raise HTTPException(status_code=503, detail="Dosya şu an indirilemiyor.") from hata


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
    arka_plan.add_task(kart_hazirlama.karti_hazirla, kart.id, kart.versiyon)
    return await kart_yaniti(oturum, kart.id)
