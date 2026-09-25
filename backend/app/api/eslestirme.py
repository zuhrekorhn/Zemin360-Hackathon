"""Eşleştirme Ajanı uç noktaları (docs/api-contracts.md § Eşleştirme).

`/eslestirme/calistir` sözleşmede "arka plan işi" olarak geçiyor: Genç ile
Kurum aynı anda platformda olmak zorunda değil. Gerçek bir cron/kuyruk
altyapısı kurmuyoruz (bilinçli, bkz. docs/architecture.md) — bu uç nokta
ileride bir zamanlayıcının çağıracağı "asıl işi yapan" kanca; şimdilik
doğrudan da çağrılabiliyor.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.eslestirme import (
    DURUM_KABUL_EDILDI,
    SKOR_ESIGI,
    TOP_N,
    Aday,
    adaylari_getir,
    eslesme_ekle_ifadesi,
    gerekce_uret,
    ihtiyac_kartini_getir,
    kilit_anahtari,
    siralayip_ele,
    temizlenecekler,
)
from app.api.kimlik import rol_gerekli
from app.api.sahiplik import bulunamadi, girvak_mi, ihtiyac_kartinin_sahibi_mi
from app.api.sahiplik import kurum_id as hesabin_kurumu
from app.api.yetenek_kartlari import kart_yaniti
from app.core.llm import HizSinirHatasi, ModelMesgulHatasi
from app.db.session import get_session, get_sessionmaker
from app.models.eslesme import Eslesme
from app.models.hesap import ROL_GIRVAK, ROL_KURUM, Hesap
from app.models.isbirligi import Isbirligi
from app.schemas.eslestirme import (
    EslestirmeCalistirIstegi,
    IlgileniyorumIstegi,
    IlgileniyorumYaniti,
    OnerilerYaniti,
    OneriYaniti,
)

logger = logging.getLogger("zemin360.eslestirme")

router = APIRouter(prefix="/eslestirme", tags=["eslestirme"])

ISBIRLIGI_AKTIF = "aktif"
IHTIYAC_YOK = "Kuruma ait ihtiyaç kartı yok"


def _hedef_kurum(hesap: Hesap, istenen: uuid.UUID | None) -> uuid.UUID:
    """Hangi kurumun eşleştirmesi? Kurum yalnızca kendisininkini, GİRVAK herhangi birini.

    Kurum başka bir kurumun kimliğini verirse 404 (sahiplik sözleşmesi,
    app/api/sahiplik.py); kimlik vermezse kendi kurumu kullanılır.
    """
    if girvak_mi(hesap):
        if istenen is None:
            raise HTTPException(status_code=422, detail="Hangi kurum için? kurum_id gerekli.")
        return istenen
    kendi = hesabin_kurumu(hesap)
    if kendi is None or (istenen is not None and istenen != kendi):
        raise bulunamadi(IHTIYAC_YOK)
    return kendi


@router.post("/calistir", response_model=OnerilerYaniti)
async def calistir(
    istek: EslestirmeCalistirIstegi,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM, ROL_GIRVAK)),
    oturum: AsyncSession = Depends(get_session),
) -> OnerilerYaniti:
    return await _pipeline_calistir(oturum, _hedef_kurum(hesap, istek.kurum_id))


@router.get("/oneriler/{kurum_id}", response_model=OnerilerYaniti)
async def oneriler(
    kurum_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM, ROL_GIRVAK)),
    oturum: AsyncSession = Depends(get_session),
) -> OnerilerYaniti:
    """Hesaplanmış önerileri sıralı döner; hiç hesaplanmamışsa pipeline'ı tetikler."""
    kurum_id = _hedef_kurum(hesap, kurum_id)
    ihtiyac = await ihtiyac_kartini_getir(oturum, kurum_id)
    if ihtiyac is None:
        raise bulunamadi(IHTIYAC_YOK)

    mevcut = await _eslesmeleri_oku(oturum, ihtiyac.id)
    if not mevcut:
        return await _pipeline_calistir(oturum, kurum_id)

    return await _yanit_kur(oturum, ihtiyac.id, mevcut)


@router.post("/ilgileniyorum", response_model=IlgileniyorumYaniti)
async def ilgileniyorum(
    istek: IlgileniyorumIstegi,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> IlgileniyorumYaniti:
    """Kurum ilgilendiğini söyler: eşleşme kabul edilir, iş birliği açılır.

    Ayrı bir kabul adımı yok — MVP kararı. Genç'e bildirim gitmesi Faz 3+
    kapsamında (şu an bilinçli olarak yok).
    """
    eslesme = await oturum.scalar(
        select(Eslesme)
        .options(selectinload(Eslesme.isbirligi), selectinload(Eslesme.ihtiyac_karti))
        .where(Eslesme.id == istek.eslesme_id)
    )
    # Yalnızca eşleşmenin ihtiyaç kartının sahibi kurum.
    if eslesme is None or not ihtiyac_kartinin_sahibi_mi(hesap, eslesme.ihtiyac_karti):
        raise bulunamadi("Eşleşme bulunamadı")

    eslesme.durum = DURUM_KABUL_EDILDI
    eslesme.son_aktivite_tarihi = dt.datetime.now(dt.UTC)

    isbirligi = eslesme.isbirligi
    if isbirligi is None:
        isbirligi = Isbirligi(
            eslesme_id=eslesme.id,
            baslangic_tarihi=dt.date.today(),
            durum=ISBIRLIGI_AKTIF,
        )
        oturum.add(isbirligi)

    await oturum.commit()

    return IlgileniyorumYaniti(
        eslesme_id=eslesme.id,
        durum=eslesme.durum,
        isbirligi_id=isbirligi.id,
        isbirligi_durum=isbirligi.durum,
    )


async def eslestirmeyi_arka_planda_calistir(kurum_id: uuid.UUID) -> None:
    """İhtiyaç kartı onaylanınca eşleştirmeyi yanıt gönderildikten sonra başlatır.

    Kurum öneriler sayfasına geldiğinde hesap çoğunlukla bitmiş oluyor; bitmemişse
    `GET /oneriler` zaten kendi başına hesaplıyor, yani bu bir hızlandırma —
    doğruluğun ona bağlı olduğu bir adım değil.

    Zamanlayıcı kurmuyoruz (bkz. CLAUDE.md): bu da bir isteğin tetiklediği iş,
    periyodik bir görev değil. Kendi oturumunu açıyor, çünkü isteğin oturumu
    yanıtla birlikte kapanıyor. Hata olursa yutuluyor: kullanıcı kartını zaten
    onayladı, arka plandaki hesap yüzünden bir şey kaybetmemeli.
    """
    async with get_sessionmaker()() as oturum:
        try:
            await _pipeline_calistir(oturum, kurum_id)
        except HTTPException as hata:
            logger.info("Arka plan eşleştirme atlandı (%s): %s", kurum_id, hata.detail)
        except Exception:
            logger.exception("Arka plan eşleştirme başarısız (%s)", kurum_id)


# --- Pipeline --------------------------------------------------------------


async def _pipeline_calistir(oturum: AsyncSession, kurum_id: uuid.UUID) -> OnerilerYaniti:
    ihtiyac = await ihtiyac_kartini_getir(oturum, kurum_id)
    if ihtiyac is None:
        raise bulunamadi(IHTIYAC_YOK)
    if ihtiyac.embedding is None:
        raise HTTPException(
            status_code=409, detail="İhtiyaç kartının embedding'i yok; kart yeniden onaylanmalı"
        )

    # Aynı ihtiyaç kartı için pipeline'lar sıraya girer: kart onaylanınca
    # arka plan işi başlıyor, kurum da o sırada öneriler sayfasını açınca
    # GET /oneriler ikinci bir pipeline başlatıyordu — mükerrer satır ve çift
    # LLM çağrısı. İkinci çağrı burada birincinin commit'ini bekler, sonra
    # kayıtları ve gerekçeleri hazır bulur. Kilit transaction sonunda kalkar.
    await oturum.execute(
        text("SELECT pg_advisory_xact_lock(:anahtar)"),
        {"anahtar": kilit_anahtari(ihtiyac.id)},
    )

    secilenler = siralayip_ele(await adaylari_getir(oturum, ihtiyac))
    eskiler = await _eslesmeleri_oku(oturum, ihtiyac.id)
    mevcutlar = {e.yetenek_karti_id: e for e in eskiler}

    # Kural ya da kart değişmiş olabilir: artık seçilmeyen öneriler listede
    # kalmasın. Kurumun karar verdiği kayıtlara dokunulmuyor.
    for eskimis in temizlenecekler(eskiler, [aday.yetenek_karti.id for aday in secilenler]):
        mevcutlar.pop(eskimis.yetenek_karti_id, None)
        await oturum.delete(eskimis)

    for aday in secilenler:
        eslesme = mevcutlar.get(aday.yetenek_karti.id)
        if eslesme is None:
            await oturum.execute(
                eslesme_ekle_ifadesi(
                    ihtiyac_karti_id=ihtiyac.id,
                    yetenek_karti_id=aday.yetenek_karti.id,
                    skor=aday.skor,
                )
            )
        else:
            # Kurumun verdiği karar (ilgileniliyor/kabul/red) ezilmez;
            # yalnızca skor tazelenir.
            eslesme.skor = aday.skor

    # Eklenenler ON CONFLICT ile yazıldı; ORM nesneleri yeniden okunarak alınır.
    guncel = {e.yetenek_karti_id: e for e in await _eslesmeleri_oku(oturum, ihtiyac.id)}
    gerekce_bekleyenler: list[tuple[Eslesme, Aday]] = [
        (guncel[aday.yetenek_karti.id], aday)
        for aday in secilenler
        if aday.yetenek_karti.id in guncel and guncel[aday.yetenek_karti.id].gerekce_metni is None
    ]

    # Gerekçeler birbirinden bağımsız: sırayla beklemek Top-5'te kullanıcıyı
    # beş çağrı boyunca bekletiyordu. Hepsi aynı anda gidiyor.
    if gerekce_bekleyenler:
        metinler = await asyncio.gather(
            *(_gerekce(ihtiyac, aday) for _, aday in gerekce_bekleyenler)
        )
        for (eslesme, _), metin in zip(gerekce_bekleyenler, metinler, strict=True):
            eslesme.gerekce_metni = metin

    await oturum.commit()

    return await _yanit_kur(oturum, ihtiyac.id, await _eslesmeleri_oku(oturum, ihtiyac.id))


async def _gerekce(ihtiyac, aday: Aday) -> str | None:
    """Gerekçeyi üretir; LLM erişilemezse eşleşmeyi gerekçesiz bırakır.

    Skor ve sıralama LLM'den bağımsız — hız sınırı ya da sağlayıcı arızası yüzünden
    tüm öneri listesini kaybetmek mantıksız olurdu. Gerekçe NULL kalır,
    sonraki çalıştırmada yeniden denenir (arayüz bunu açıkça söylüyor).
    """
    try:
        return await gerekce_uret(ihtiyac, aday)
    except (HizSinirHatasi, ModelMesgulHatasi):
        return None


async def _eslesmeleri_oku(oturum: AsyncSession, ihtiyac_karti_id: uuid.UUID) -> list[Eslesme]:
    satirlar = await oturum.scalars(
        select(Eslesme)
        .where(Eslesme.ihtiyac_karti_id == ihtiyac_karti_id)
        .order_by(Eslesme.skor.desc())
    )
    return list(satirlar)


async def _yanit_kur(
    oturum: AsyncSession, ihtiyac_karti_id: uuid.UUID, eslesmeler: list[Eslesme]
) -> OnerilerYaniti:
    oneriler = [
        OneriYaniti(
            eslesme_id=eslesme.id,
            skor=round(eslesme.skor, 4),
            durum=eslesme.durum,
            gerekce_metni=eslesme.gerekce_metni,
            yetenek_karti=await kart_yaniti(oturum, eslesme.yetenek_karti_id),
        )
        for eslesme in eslesmeler
    ]
    return OnerilerYaniti(
        ihtiyac_karti_id=ihtiyac_karti_id,
        oneriler=oneriler,
        # Cold start: havuz küçükken bunu arayüzde gizleme (matching-algorithm.md § 5)
        az_sonuc_uyarisi=len(oneriler) < TOP_N,
        skor_esigi=SKOR_ESIGI,
    )
