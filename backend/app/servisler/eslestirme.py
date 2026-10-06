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
    BILINMIYOR,
    DURUM_GENC_ILGILENDI,
    DURUM_KABUL_EDILDI,
    DURUM_ONERILDI,
    TOP_N,
    Aday,
    FirmaAdayi,
    Yargi,
    aday_ekle_ifadesi,
    aday_kimligi,
    adaylari_getir,
    firma_adaylarini_getir,
    firma_gerekce_uret,
    firma_uygunluk_yargila,
    gerekce_uret,
    kilit_anahtari,
    siralayip_ele,
    temizlenecekler,
)
from app.agents.uygunluk import (
    UYGUN_DEGIL,
    YARGI_N,
    gorunur_kosulu,
    listelenecekler,
)
from app.api.bildirimler import bildirim_ekle
from app.api.sahiplik import eslesmedeki_taraf
from app.core.ilan import ARANAN_FIRMA
from app.core.llm import HizSinirHatasi, ModelMesgulHatasi
from app.db.session import get_sessionmaker
from app.models.bildirim import TUR_YENI_ONERI
from app.models.eslesme import Eslesme
from app.models.firma_karti import FirmaKarti
from app.models.hesap import Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kurum import Kurum
from app.models.yetenek_karti import YetenekKarti
from app.schemas.eslestirme import Iletisim

logger = logging.getLogger("zemin360.eslestirme")

IHTIYAC_HAZIR_DEGIL = (
    "Bu ihtiyaç henüz adaylarla eşleştirilmeye hazır değil. Biraz sonra yeniden deneyin."
)

IHTIYAC_ACIK = "acik"
# Firmaya görünür (docs/icerik-rehberi.md: "siz", teknik terim yok).
IHTIYAC_KAPALI_MESAJI = "Bu ihtiyaç kapandı; yeni aday aranmıyor."


def iliskileriyle(sorgu):
    """İletişim bilgisi ve sahiplik için gereken ilişkiler: iki taraf ve iş birliği.

    Aday ya yetenek kartı (genci) ya firma kartı (firması); ikisi de yüklenir.
    """
    return sorgu.options(
        selectinload(Eslesme.yetenek_karti).selectinload(YetenekKarti.kullanici),
        selectinload(Eslesme.firma_karti).selectinload(FirmaKarti.kurum),
        selectinload(Eslesme.ihtiyac_karti).selectinload(IhtiyacKarti.kurum),
        selectinload(Eslesme.isbirligi),
    )


async def eslesmeleri_oku(
    oturum: AsyncSession, ihtiyac_karti_id: uuid.UUID, *, gizliler_dahil: bool = False
) -> list[Eslesme]:
    """İhtiyacın eşleşmeleri, skora göre. `uygun_degil` kayıtlar varsayılan olarak yok.

    `gizliler_dahil=True` yalnızca pipeline'ın kendi içindir (tekrar yargılamamak
    için saklanan kayıtları görmesi gerekir); hiçbir yanıta gitmez.
    """
    sorgu = iliskileriyle(select(Eslesme)).where(Eslesme.ihtiyac_karti_id == ihtiyac_karti_id)
    if not gizliler_dahil:
        sorgu = sorgu.where(gorunur_kosulu())
    return list(await oturum.scalars(sorgu.order_by(Eslesme.skor.desc())))


def iletisim(eslesme: Eslesme, hesap: Hesap | None) -> Iletisim | None:
    """E-postalar yalnızca `kabul_edildi`'de ve yalnızca iki taraftan birine.

    GİRVAK okuma yetkisiyle her şeyi görür ama iletişim bilgisi onun işi
    değil. `eslesme` ilişkileriyle yüklenmiş olmalı (`iliskileriyle`).
    """
    if eslesme.durum != DURUM_KABUL_EDILDI or hesap is None:
        return None
    if eslesmedeki_taraf(hesap, eslesme) is None:
        return None
    if eslesme.firma_karti is not None:
        # Firma–firma: aday firmanın e-postası ayrı alanda (genç ekranları değişmez).
        return Iletisim(
            aday_firma_email=eslesme.firma_karti.kurum.iletisim_email,
            kurum_email=eslesme.ihtiyac_karti.kurum.iletisim_email,
        )
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
        raise HTTPException(status_code=409, detail=IHTIYAC_HAZIR_DEGIL)
    if ihtiyac.durum != IHTIYAC_ACIK:
        # Kapalı ihtiyaç için aday aranmaz; mevcut kayıtlar okunabilir kalır.
        raise HTTPException(status_code=409, detail=IHTIYAC_KAPALI_MESAJI)

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

    # Aday kaynağı ilana göre (docs/plans/firma-akisi.md § 4): genç ilanında
    # yetenek kartları, ortak ilanında firma kartları. Gençler ortak ilanına,
    # firmalar genç ilanına önerilmez. Firma–firma'da benzerlik tabanını geçen
    # ilk YARGI_N aday yapay zekâ tarafından yargılanır (docs/matching-algorithm.md
    # § 8); genç tarafı eskisi gibi doğrudan ilk TOP_N.
    firma_ilani = ihtiyac.aranan == ARANAN_FIRMA
    aday_kaynagi = firma_adaylarini_getir if firma_ilani else adaylari_getir
    adaylar = await aday_kaynagi(oturum, ihtiyac)
    # Gizli (`uygun_degil`) kayıtlar da okunur: yeniden yargılanmasınlar diye.
    eskiler = await eslesmeleri_oku(oturum, ihtiyac.id, gizliler_dahil=True)
    mevcutlar = {aday_kimligi(e): e for e in eskiler}
    if firma_ilani:
        secilenler, yargilar = await _firma_adaylarini_yargila(ihtiyac, adaylar, mevcutlar)
    else:
        secilenler, yargilar = siralayip_ele(adaylar), {}

    # Kural ya da kart değişmiş olabilir: artık seçilmeyen öneriler listede
    # kalmasın. Kurumun karar verdiği kayıtlara dokunulmuyor.
    for eskimis in temizlenecekler(eskiler, [aday.aday_kimligi for aday in secilenler]):
        mevcutlar.pop(aday_kimligi(eskimis), None)
        await oturum.delete(eskimis)

    yeni_oneri = 0
    for aday in secilenler:
        eslesme = mevcutlar.get(aday.aday_kimligi)
        if eslesme is None:
            # ON CONFLICT DO NOTHING: aynı anda çalışan başka bir pipeline
            # eklemişse rowcount 0, bildirimde iki kez sayılmaz.
            eklenen = await oturum.execute(aday_ekle_ifadesi(ihtiyac.id, aday))
            # Gizli kayıt için "yeni aday var" bildirimi yazılmaz.
            if _karar(yargilar, aday) != UYGUN_DEGIL:
                yeni_oneri += eklenen.rowcount
        elif eslesme.durum != DURUM_GENC_ILGILENDI:
            # Kurumun verdiği karar (ilgileniliyor/kabul/red) ezilmez;
            # yalnızca skor tazelenir. Gencin ilgi gösterdiği kaydın skoru da
            # değişmez (plan § 0, karar 14): genç o uyumu görerek ilgilendi.
            eslesme.skor = aday.skor

    # Eklenenler ON CONFLICT ile yazıldı; ORM nesneleri yeniden okunarak alınır.
    guncel = {
        aday_kimligi(e): e for e in await eslesmeleri_oku(oturum, ihtiyac.id, gizliler_dahil=True)
    }
    # Yargı yalnızca bu hesapta yargılanan kayıtlara yazılır (karar verilmiş kayıt hiç
    # yargılanmadı). Başarısız çağrı ("bilinmiyor") kayda dokunmaz: eski gerekçe kalır.
    for kimlik, yargi in yargilar.items():
        if yargi.uygunluk is not None and kimlik in guncel:
            guncel[kimlik].gerekce_metni = yargi.gerekce
            guncel[kimlik].uygunluk = yargi.uygunluk

    gerekce_bekleyenler: list[tuple[Eslesme, Aday | FirmaAdayi]] = [
        (guncel[aday.aday_kimligi], aday)
        for aday in secilenler
        if aday.aday_kimligi in guncel
        and guncel[aday.aday_kimligi].gerekce_metni is None
        # Adayın ilgi gösterdiği kaydın gerekçesi değiştirilmez (karar 14).
        and guncel[aday.aday_kimligi].durum != DURUM_GENC_ILGILENDI
        # Firma–firma'da öneri gerekçesini yargı çağrısı yazar (başarısızsa sonraki
        # hesapta yeniden denenir); burada yalnızca karar verilmiş kayıtların
        # eksik gerekçesi eski yoldan tamamlanır, yargılanmaz.
        and not (firma_ilani and guncel[aday.aday_kimligi].durum == DURUM_ONERILDI)
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
            f"İhtiyacınız için {yeni_oneri} yeni aday var.",
        )

    await oturum.commit()

    return await eslesmeleri_oku(oturum, ihtiyac.id)


def _karar(yargilar: dict[uuid.UUID, Yargi], aday: Aday | FirmaAdayi) -> str | None:
    yargi = yargilar.get(aday.aday_kimligi)
    return yargi.uygunluk if yargi else None


def yargilanmali_mi(eslesme: Eslesme | None) -> bool:
    """Bu aday için model çağrısı gerekir mi?

    Kayıt yoksa evet. `onerildi` kayıt kararsızsa (eski kayıt, hata almış çağrı,
    kart değişince sıfırlanmış) evet. Kararı olan kayıt bir daha yargılanmaz; karar
    verilmiş kayıt (ilgileniliyor, genc_ilgilendi, kabul_edildi, reddedildi, kapandi)
    hiçbir zaman yargılanmaz (karar 14).
    """
    if eslesme is None:
        return True
    return eslesme.durum == DURUM_ONERILDI and eslesme.uygunluk is None


async def _firma_adaylarini_yargila(
    ihtiyac: IhtiyacKarti,
    adaylar: list[FirmaAdayi],
    mevcutlar: dict[uuid.UUID, Eslesme],
) -> tuple[list[FirmaAdayi], dict[uuid.UUID, Yargi]]:
    """Skora göre ilk YARGI_N adaydan `uygun_degil` olmayan ilk TOP_N'i seçer.

    Adaylar skor sırasıyla dalgalar halinde yargılanır: listelenecek ilk TOP_N'in
    kararsız olanları aynı anda gider, elenen çıkarsa sıradaki aday yargılanır;
    pencere (YARGI_N) dolunca ya da listede kararsız aday kalmayınca biter.
    Sonuç, hepsi pencerede yargılansaydı çıkacak listenin aynısı ama yalnızca
    gereken çağrılar yapılır. Yargılanmış her aday (elenenler dahil) kaydedilir:
    bir sonraki hesap onlar için model çağırmaz.

    Hata alan çağrı "bilinmiyor" sayılır: aday bugünkü gibi listelenir, gerekçesiz;
    aynı hesapta bir daha denenmez, sonraki hesapta denenir.

    Döner: (saklanacak adaylar, bu hesapta verilen yargılar). Saklanacaklar listelenecekler
    ve gizli kalacak elenenlerdir; pencerede olup ikisi de olmayanlar saklanmaz.
    """
    pencere = siralayip_ele(adaylar, YARGI_N)
    kimlikler = [aday.aday_kimligi for aday in pencere]
    adaya = {aday.aday_kimligi: aday for aday in pencere}
    kararlar: dict[uuid.UUID, str | None] = {
        kimlik: mevcutlar[kimlik].uygunluk for kimlik in kimlikler if kimlik in mevcutlar
    }
    yargilar: dict[uuid.UUID, Yargi] = {}
    denenenler: set[uuid.UUID] = set()

    while True:
        liste = listelenecekler(kimlikler, kararlar, TOP_N)
        bekleyenler = [
            adaya[kimlik]
            for kimlik in liste
            if kimlik not in denenenler and yargilanmali_mi(mevcutlar.get(kimlik))
        ]
        if not bekleyenler:
            break
        sonuclar = await asyncio.gather(*(_yargila(ihtiyac, aday) for aday in bekleyenler))
        for aday, yargi in zip(bekleyenler, sonuclar, strict=True):
            denenenler.add(aday.aday_kimligi)
            yargilar[aday.aday_kimligi] = yargi
            kararlar[aday.aday_kimligi] = yargi.uygunluk

    saklanacak = set(listelenecekler(kimlikler, kararlar, TOP_N)) | {
        kimlik for kimlik in kimlikler if kararlar.get(kimlik) == UYGUN_DEGIL
    }
    return [adaya[kimlik] for kimlik in kimlikler if kimlik in saklanacak], yargilar


async def _yargila(ihtiyac: IhtiyacKarti, aday: FirmaAdayi) -> Yargi:
    """Yargı çağrısı; her hata "bilinmiyor". `uygun_degil` hiçbir hatada üretilmez.

    Skor ve sıralama modelden bağımsız: model erişilemezse, zaman aşımına uğrarsa ya da
    geçersiz çıktı verirse öneri bugünkü gibi listelenir.
    """
    try:
        return await firma_uygunluk_yargila(ihtiyac, aday)
    except Exception:
        logger.warning(
            "Uygunluk yargısı alınamadı; karar bilinmiyor sayıldı (%s)",
            aday.aday_kimligi,
            exc_info=True,
        )
        return BILINMIYOR


async def _gerekce(ihtiyac, aday: Aday | FirmaAdayi) -> str | None:
    """Gerekçeyi üretir; LLM erişilemezse eşleşmeyi gerekçesiz bırakır.

    Skor ve sıralama LLM'den bağımsız — hız sınırı ya da sağlayıcı arızası yüzünden
    tüm öneri listesini kaybetmek mantıksız olurdu. Gerekçe NULL kalır,
    sonraki çalıştırmada yeniden denenir (arayüz bunu açıkça söylüyor).
    """
    try:
        if isinstance(aday, FirmaAdayi):
            return await firma_gerekce_uret(ihtiyac, aday)
        return await gerekce_uret(ihtiyac, aday)
    except (HizSinirHatasi, ModelMesgulHatasi):
        return None
