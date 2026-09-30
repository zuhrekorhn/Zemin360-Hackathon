"""Eşleştirme pipeline'ı ve eşleşmenin paylaşılan okumaları.

Pipeline üç yerden çağrılıyor: kurumun uçları (`/eslestirme/calistir`,
`/eslestirme/oneriler`), ihtiyaç kartı onayından sonraki arka plan işi ve
(genç akışında) yetenek kartı hazırlama. Kural ve skor app/agents/eslestirme.py'de;
burada veritabanı, kilit, gerekçe ve bildirim.

Yanıt şeması (`OnerilerYaniti`) API'nin işi: pipeline eşleşmeleri döner.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.eslestirme import (
    DURUM_GENC_ILGILENDI,
    DURUM_KABUL_EDILDI,
    Aday,
    adaylari_getir,
    eslesme_ekle_ifadesi,
    gerekce_uret,
    kilit_anahtari,
    siralayip_ele,
    temizlenecekler,
)
from app.api.bildirimler import bildirim_ekle
from app.api.sahiplik import eslesmedeki_taraf
from app.core.ilan import ARANAN_FIRMA
from app.core.llm import HizSinirHatasi, ModelMesgulHatasi
from app.db.session import get_sessionmaker
from app.models.bildirim import TUR_YENI_ONERI
from app.models.eslesme import Eslesme
from app.models.hesap import Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kurum import Kurum
from app.models.yetenek_karti import YetenekKarti
from app.schemas.eslestirme import Iletisim

logger = logging.getLogger("zemin360.eslestirme")

IHTIYAC_ACIK = "acik"
# Firmaya görünür (docs/icerik-rehberi.md: "siz", teknik terim yok).
IHTIYAC_KAPALI_MESAJI = "Bu ihtiyaç kapandı; yeni aday aranmıyor."


def iliskileriyle(sorgu):
    """İletişim bilgisi ve sahiplik için gereken ilişkiler: iki taraf ve iş birliği."""
    return sorgu.options(
        selectinload(Eslesme.yetenek_karti).selectinload(YetenekKarti.kullanici),
        selectinload(Eslesme.ihtiyac_karti).selectinload(IhtiyacKarti.kurum),
        selectinload(Eslesme.isbirligi),
    )


async def eslesmeleri_oku(oturum: AsyncSession, ihtiyac_karti_id: uuid.UUID) -> list[Eslesme]:
    satirlar = await oturum.scalars(
        iliskileriyle(select(Eslesme))
        .where(Eslesme.ihtiyac_karti_id == ihtiyac_karti_id)
        .order_by(Eslesme.skor.desc())
    )
    return list(satirlar)


def iletisim(eslesme: Eslesme, hesap: Hesap | None) -> Iletisim | None:
    """E-postalar yalnızca `kabul_edildi`'de ve yalnızca iki taraftan birine.

    GİRVAK okuma yetkisiyle her şeyi görür ama iletişim bilgisi onun işi
    değil. `eslesme` ilişkileriyle yüklenmiş olmalı (`iliskileriyle`).
    """
    if eslesme.durum != DURUM_KABUL_EDILDI or hesap is None:
        return None
    if eslesmedeki_taraf(hesap, eslesme) is None:
        return None
    return Iletisim(
        genc_email=eslesme.yetenek_karti.kullanici.email,
        kurum_email=eslesme.ihtiyac_karti.kurum.iletisim_email,
    )


async def eslestirmeyi_arka_planda_calistir(ihtiyac_karti_id: uuid.UUID) -> None:
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
            ihtiyac = await oturum.get(IhtiyacKarti, ihtiyac_karti_id)
            if ihtiyac is not None:
                await pipeline_calistir(oturum, ihtiyac)
        except HTTPException as hata:
            logger.info("Arka plan eşleştirme atlandı (%s): %s", ihtiyac_karti_id, hata.detail)
        except Exception:
            logger.exception("Arka plan eşleştirme başarısız (%s)", ihtiyac_karti_id)


async def ihtiyac_kilidi(oturum: AsyncSession, ihtiyac_karti_id: uuid.UUID) -> None:
    """İhtiyaç başına işlem kilidi: pipeline'lar ve ilan kapatma sıraya girer."""
    await oturum.execute(
        text("SELECT pg_advisory_xact_lock(:anahtar)"),
        {"anahtar": kilit_anahtari(ihtiyac_karti_id)},
    )


async def pipeline_calistir(oturum: AsyncSession, ihtiyac: IhtiyacKarti) -> list[Eslesme]:
    """Adayları seçer, eşleşmeleri yazar, gerekçeleri üretir; güncel eşleşmeleri döner."""
    if ihtiyac.embedding is None:
        raise HTTPException(
            status_code=409, detail="İhtiyaç kartının embedding'i yok; kart yeniden onaylanmalı"
        )
    if ihtiyac.durum != IHTIYAC_ACIK:
        # Kapalı ihtiyaç için aday aranmaz; mevcut kayıtlar okunabilir kalır.
        raise HTTPException(status_code=409, detail=IHTIYAC_KAPALI_MESAJI)
    if ihtiyac.aranan == ARANAN_FIRMA:
        # Ortak ilanının adayları firmalar (docs/plans/firma-akisi.md § 4); gençler
        # bu ilana önerilmez. Firma adayları eklenene kadar liste boş kalır.
        return await eslesmeleri_oku(oturum, ihtiyac.id)

    # Aynı ihtiyaç kartı için pipeline'lar sıraya girer: kart onaylanınca
    # arka plan işi başlıyor, kurum da o sırada öneriler sayfasını açınca
    # GET /oneriler ikinci bir pipeline başlatıyordu — mükerrer satır ve çift
    # LLM çağrısı. İkinci çağrı burada birincinin commit'ini bekler, sonra
    # kayıtları ve gerekçeleri hazır bulur. Kilit transaction sonunda kalkar.
    await ihtiyac_kilidi(oturum, ihtiyac.id)
    # Kilidi beklerken ilan kapatılmış olabilir (kapatma da bu kilidi alıyor):
    # durum kilitten sonra yeniden okunur, kapalı ilana öneri yazılmaz.
    guncel_durum = await oturum.scalar(
        select(IhtiyacKarti.durum).where(IhtiyacKarti.id == ihtiyac.id)
    )
    if guncel_durum != IHTIYAC_ACIK:
        raise HTTPException(status_code=409, detail=IHTIYAC_KAPALI_MESAJI)

    secilenler = siralayip_ele(await adaylari_getir(oturum, ihtiyac))
    eskiler = await eslesmeleri_oku(oturum, ihtiyac.id)
    mevcutlar = {e.yetenek_karti_id: e for e in eskiler}

    # Kural ya da kart değişmiş olabilir: artık seçilmeyen öneriler listede
    # kalmasın. Kurumun karar verdiği kayıtlara dokunulmuyor.
    for eskimis in temizlenecekler(eskiler, [aday.yetenek_karti.id for aday in secilenler]):
        mevcutlar.pop(eskimis.yetenek_karti_id, None)
        await oturum.delete(eskimis)

    yeni_oneri = 0
    for aday in secilenler:
        eslesme = mevcutlar.get(aday.yetenek_karti.id)
        if eslesme is None:
            # ON CONFLICT DO NOTHING: aynı anda çalışan başka bir pipeline
            # eklemişse rowcount 0, bildirimde iki kez sayılmaz.
            eklenen = await oturum.execute(
                eslesme_ekle_ifadesi(
                    ihtiyac_karti_id=ihtiyac.id,
                    yetenek_karti_id=aday.yetenek_karti.id,
                    skor=aday.skor,
                )
            )
            yeni_oneri += eklenen.rowcount
        elif eslesme.durum != DURUM_GENC_ILGILENDI:
            # Kurumun verdiği karar (ilgileniliyor/kabul/red) ezilmez;
            # yalnızca skor tazelenir. Gencin ilgi gösterdiği kaydın skoru da
            # değişmez (plan § 0, karar 14): genç o uyumu görerek ilgilendi.
            eslesme.skor = aday.skor

    # Eklenenler ON CONFLICT ile yazıldı; ORM nesneleri yeniden okunarak alınır.
    guncel = {e.yetenek_karti_id: e for e in await eslesmeleri_oku(oturum, ihtiyac.id)}
    gerekce_bekleyenler: list[tuple[Eslesme, Aday]] = [
        (guncel[aday.yetenek_karti.id], aday)
        for aday in secilenler
        if aday.yetenek_karti.id in guncel
        and guncel[aday.yetenek_karti.id].gerekce_metni is None
        # Gencin ilgi gösterdiği kaydın gerekçesi değiştirilmez (karar 14).
        and guncel[aday.yetenek_karti.id].durum != DURUM_GENC_ILGILENDI
    ]

    # Gerekçeler birbirinden bağımsız: sırayla beklemek Top-5'te kullanıcıyı
    # beş çağrı boyunca bekletiyordu. Hepsi aynı anda gidiyor.
    if gerekce_bekleyenler:
        metinler = await asyncio.gather(
            *(_gerekce(ihtiyac, aday) for _, aday in gerekce_bekleyenler)
        )
        for (eslesme, _), metin in zip(gerekce_bekleyenler, metinler, strict=True):
            eslesme.gerekce_metni = metin

    if yeni_oneri:
        bildirim_ekle(
            oturum,
            await oturum.scalar(select(Kurum.hesap_id).where(Kurum.id == ihtiyac.kurum_id)),
            TUR_YENI_ONERI,
            f"İhtiyaç kartın için {yeni_oneri} yeni öneri var.",
        )

    await oturum.commit()

    return await eslesmeleri_oku(oturum, ihtiyac.id)


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
