"""Firma kartı uçları (docs/plans/firma-akisi.md § 0 kararlar 3, 9, 10; § 5).

Kart sohbetle oluşur (onay ucu sohbetle birlikte); burada firmanın kendi
kartını okuması ve formla düzenlemesi. Yalnızca firma, yalnızca kendi kartı:
kart token'daki firmanın kartı, başkasının kartı diye bir yol yok. Genç ve
GİRVAK 403, token yok 401.

Düzenleme, yetenek kartındaki gibi: satır kilitli okunur (aynı anda iki
düzenleme versiyonu ezmesin), gerçek değişiklikte versiyon artar ve firmanın
ne yaptığını anlatan alanlar değiştiyse kart yanıttan sonra yeniden hazırlanır.
Aynı değerle gelen düzenleme hiçbir şeyi tetiklemez.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.kimlik import rol_gerekli
from app.api.sahiplik import bulunamadi
from app.core.firma_karti import ZORUNLU_ALANLAR
from app.db.session import get_session
from app.models.firma_karti import FirmaKarti
from app.models.hesap import ROL_KURUM, Hesap
from app.schemas.firma_karti import FirmaKartiGuncelleme, FirmaKartiYaniti
from app.servisler import firma_karti as servis

router = APIRouter(prefix="/kurum/kart", tags=["firma-karti"])

KART_YOK = "Firma kartınız henüz yok."


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
