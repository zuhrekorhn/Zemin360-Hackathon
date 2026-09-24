"""Doğrulama Ajanı uç noktaları (docs/api-contracts.md § Doğrulama).

Akışlar docs/sequence-diagrams.md § Akış 2'den:
  kanıt ekle → ön rubrik + referans isteği → (yanıt | zaman aşımı) → itiraz.

Zaman aşımı için zamanlayıcı yok: `bekliyor` → `yanit_yok` geçişi kanıt
durumu okunduğu anda hesaplanıyor (Eşleştirme'deki cron'suz yaklaşımın aynısı).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.dogrulama import (
    DURUM_BEKLIYOR,
    DURUM_YANIT_YOK,
    DURUM_YANITLANDI,
    LinkKontrolu,
    linki_kontrol_et,
    rubrik_puanla,
    ucuncu_taraf_onayi_hesapla,
    zaman_asimina_ugradi_mi,
)
from app.core.llm import HizSinirHatasi
from app.db.session import get_session
from app.models.guven_skoru import GuvenSkoru
from app.models.referans_istegi import ReferansIstegi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.dogrulama import (
    GuvenSkoruYaniti,
    ItirazIstegi,
    KanitDurumuYaniti,
    KanitEkleIstegi,
    ReferansDurumuYaniti,
    ReferansIstegiYaniti,
    ReferansYanitiIstegi,
)

router = APIRouter(prefix="/dogrulama", tags=["dogrulama"])

# Referans kişiye gönderilecek girişsiz yanıt adresi. Gerçek e-posta
# göndermiyoruz (SMTP yok, MVP kararı) — link API yanıtında dönüyor.
YANIT_YOLU = "/dogrulama/referans-yaniti?token={token}"


@router.post("/kanit-ekle", response_model=KanitDurumuYaniti, status_code=201)
async def kanit_ekle(
    istek: KanitEkleIstegi, oturum: AsyncSession = Depends(get_session)
) -> KanitDurumuYaniti:
    """Kanıtı kaydeder, erişilebilirliğini sınar, ön rubrik puanını üretir."""
    cikti = await _ciktiyi_getir(oturum, istek.somut_cikti_id)

    if istek.kanit_linki:
        cikti.kanit_linki = istek.kanit_linki
    if istek.kanit_turu:
        cikti.kanit_turu = istek.kanit_turu

    kontrol = await linki_kontrol_et(cikti.kanit_linki)
    await _rubrigi_yaz(cikti, kontrol)

    if istek.referans_email:
        cikti.referans_istekleri.append(ReferansIstegi(referans_email=str(istek.referans_email)))

    await _kanit_bekleyen_guncelle(oturum, cikti.yetenek_karti_id)
    await oturum.commit()

    return await _durum_yaniti(oturum, cikti.id, kontrol.erisilebilir)


@router.post("/referans-yaniti", response_model=KanitDurumuYaniti)
async def referans_yaniti(
    istek: ReferansYanitiIstegi, oturum: AsyncSession = Depends(get_session)
) -> KanitDurumuYaniti:
    """Token ile bulunur, giriş gerektirmez (api-contracts.md § Mimari Notlar)."""
    referans = await oturum.scalar(
        select(ReferansIstegi).where(ReferansIstegi.token == istek.token)
    )
    if referans is None:
        raise HTTPException(status_code=404, detail="Referans isteği bulunamadı")

    # Zaman aşımı burada da uygulanıyor: GET "yanıtlanamaz" derken POST'un
    # yanıtı kabul etmesi, iki uç noktanın farklı kural işletmesi olurdu.
    if _zaman_asimini_isle(referans):
        await oturum.commit()
    _yanitlanabilirligi_dogrula(referans)

    referans.durum = DURUM_YANITLANDI
    referans.yanit_metni = istek.yorum
    referans.puan = istek.puan

    cikti = await _ciktiyi_getir(oturum, referans.somut_cikti_id)
    if cikti.guven_skoru is None:
        # Kanıt puanlanmadan referans gelirse skor kaydı yoksa aç; diğer
        # bileşenler 0 kalır, kanıt eklendiğinde/itirazda hesaplanır.
        cikti.guven_skoru = GuvenSkoru(
            kanit_orijinalligi=0,
            sonuc_olculebilirligi=0,
            rol_netligi=0,
            ucuncu_taraf_onayi=0,
            gerekce_metni=None,
        )
    # Birden fazla referans yanıtlamış olabilir; son gelen öncekini ezmesin.
    cikti.guven_skoru.ucuncu_taraf_onayi = ucuncu_taraf_onayi_hesapla(
        [r.puan for r in cikti.referans_istekleri if r.puan is not None]
    )

    await oturum.commit()
    return await _durum_yaniti(oturum, cikti.id, None)


@router.get("/referans/{token}", response_model=ReferansIstegiYaniti)
async def referans_istegi_goruntule(
    token: str, oturum: AsyncSession = Depends(get_session)
) -> ReferansIstegiYaniti:
    """Referans kişinin yanıt sayfası için: neyi onaylıyor?

    Girişsiz, token bazlı (yanıt uç noktasıyla aynı gerekçe). Zaman aşımı
    burada da okuma anında hesaplanıyor — süresi geçmiş bir linke form
    gösterip sonra reddetmek olmaz.
    """
    referans = await oturum.scalar(
        select(ReferansIstegi)
        .options(
            selectinload(ReferansIstegi.somut_cikti)
            .selectinload(SomutCikti.yetenek_karti)
            .selectinload(YetenekKarti.kullanici)
        )
        .where(ReferansIstegi.token == token)
    )
    if referans is None:
        raise HTTPException(status_code=404, detail="Bu referans linki geçersiz")

    if _zaman_asimini_isle(referans):
        await oturum.commit()

    return referans_gorunumu(referans)


@router.get("/kanit/{somut_cikti_id}", response_model=KanitDurumuYaniti)
async def kanit_durumu(
    somut_cikti_id: uuid.UUID, oturum: AsyncSession = Depends(get_session)
) -> KanitDurumuYaniti:
    """Kanıtın güncel durumu.

    Zaman aşımına uğramış referans istekleri bu okuma sırasında `yanit_yok`
    olarak işaretlenir — ayrı bir zamanlayıcı kurmuyoruz (bilinçli).
    """
    return await _durum_yaniti(oturum, somut_cikti_id, None)


@router.post("/itiraz", response_model=KanitDurumuYaniti)
async def itiraz(
    istek: ItirazIstegi, oturum: AsyncSession = Depends(get_session)
) -> KanitDurumuYaniti:
    """Kullanıcı skoru itiraz eder, rubrik yeniden hesaplanır.

    Skor kaydı silinmez, üzerine yazılır. Üçüncü taraf onayı korunur —
    referans zaten yanıtlamışsa itiraz onu geçersiz kılmamalı.
    """
    cikti = await _ciktiyi_getir(oturum, istek.somut_cikti_id)
    if istek.yeni_kanit_linki:
        cikti.kanit_linki = istek.yeni_kanit_linki

    kontrol = await linki_kontrol_et(cikti.kanit_linki)
    await _rubrigi_yaz(cikti, kontrol)
    await _kanit_bekleyen_guncelle(oturum, cikti.yetenek_karti_id)
    await oturum.commit()

    return await _durum_yaniti(oturum, cikti.id, kontrol.erisilebilir)


# --- Ortak parçalar --------------------------------------------------------


def _zaman_asimini_isle(referans: ReferansIstegi) -> bool:
    """Süresi dolmuşsa durumu `yanit_yok` yapar; kaydedilecek değişiklik varsa True.

    Zamanlayıcı yok (bilinçli): geçiş, kayda her dokunulduğunda hesaplanıyor.
    """
    if zaman_asimina_ugradi_mi(referans.olusturma_tarihi, referans.durum):
        referans.durum = DURUM_YANIT_YOK
        return True
    return False


def _yanitlanabilirligi_dogrula(referans: ReferansIstegi) -> None:
    """Yanıt kabul edilebilir mi? GET ve POST aynı kuralı işletsin diye ortak."""
    if referans.durum == DURUM_YANITLANDI:
        raise HTTPException(status_code=409, detail="Bu referans zaten yanıtlanmış")
    if referans.durum == DURUM_YANIT_YOK:
        raise HTTPException(
            status_code=409,
            detail="Bu referans isteğinin süresi doldu, yanıt alınamıyor.",
        )


def referans_gorunumu(referans: ReferansIstegi) -> ReferansIstegiYaniti:
    """Referans isteğini, girişsiz sayfaya açılabilecek alanlara indirger."""
    cikti = referans.somut_cikti
    return ReferansIstegiYaniti(
        somut_cikti_id=cikti.id,
        baslik=cikti.baslik,
        aciklama=cikti.aciklama,
        iddia_sahibi_adi=cikti.yetenek_karti.kullanici.ad,
        durum=referans.durum,
        yanitlanabilir=referans.durum == DURUM_BEKLIYOR,
    )


async def _ciktiyi_getir(oturum: AsyncSession, somut_cikti_id: uuid.UUID) -> SomutCikti:
    cikti = await oturum.scalar(
        select(SomutCikti)
        .options(
            selectinload(SomutCikti.guven_skoru),
            selectinload(SomutCikti.referans_istekleri),
        )
        .where(SomutCikti.id == somut_cikti_id)
    )
    if cikti is None:
        raise HTTPException(status_code=404, detail="Somut çıktı bulunamadı")
    return cikti


async def _rubrigi_yaz(cikti: SomutCikti, kontrol: LinkKontrolu) -> None:
    """Ön rubriği üretip kaydeder; üçüncü taraf onayı korunur.

    LLM kotası dolarsa 429 döner — burada sessizce puansız devam etmek
    yanlış olurdu, kullanıcı kanıtının değerlendirilmediğini bilmeli.
    """
    try:
        puan = await rubrik_puanla(
            baslik=cikti.baslik,
            aciklama=cikti.aciklama,
            kanit_linki=cikti.kanit_linki,
            kontrol=kontrol,
        )
    except HizSinirHatasi as hata:
        raise HTTPException(
            status_code=429,
            detail="LLM kotası doldu, kanıt değerlendirilemedi. Biraz sonra tekrar dene.",
        ) from hata

    if cikti.guven_skoru is None:
        cikti.guven_skoru = GuvenSkoru(
            kanit_orijinalligi=puan.kanit_orijinalligi,
            sonuc_olculebilirligi=puan.sonuc_olculebilirligi,
            rol_netligi=puan.rol_netligi,
            ucuncu_taraf_onayi=0,  # referans gelene kadar 0
            gerekce_metni=puan.gerekce_metni,
        )
    else:
        cikti.guven_skoru.kanit_orijinalligi = puan.kanit_orijinalligi
        cikti.guven_skoru.sonuc_olculebilirligi = puan.sonuc_olculebilirligi
        cikti.guven_skoru.rol_netligi = puan.rol_netligi
        cikti.guven_skoru.gerekce_metni = puan.gerekce_metni


async def _kanit_bekleyen_guncelle(oturum: AsyncSession, yetenek_karti_id: uuid.UUID) -> None:
    """Kartın `kanit_bekleyen` bayrağını çıktılarla tutarlı tutar.

    Bayrak Keşif'te kart oluşurken de aynı kuralla set ediliyordu: kanıt
    linki olmayan bir çıktı varsa kart kanıt bekliyor sayılır.
    """
    kart = await oturum.scalar(
        select(YetenekKarti)
        .options(selectinload(YetenekKarti.somut_ciktilar))
        .where(YetenekKarti.id == yetenek_karti_id)
    )
    if kart is not None:
        kart.kanit_bekleyen = any(not c.kanit_linki for c in kart.somut_ciktilar)


async def _durum_yaniti(
    oturum: AsyncSession, somut_cikti_id: uuid.UUID, link_erisilebilir: bool | None
) -> KanitDurumuYaniti:
    cikti = await _ciktiyi_getir(oturum, somut_cikti_id)

    # Zaman aşımı: okuma anında hesaplanıp kalıcılaştırılır.
    zaman_asimi_oldu = False
    for referans in cikti.referans_istekleri:
        if zaman_asimina_ugradi_mi(referans.olusturma_tarihi, referans.durum):
            referans.durum = DURUM_YANIT_YOK
            zaman_asimi_oldu = True
    if zaman_asimi_oldu:
        await oturum.commit()

    skor = cikti.guven_skoru
    return KanitDurumuYaniti(
        somut_cikti_id=cikti.id,
        baslik=cikti.baslik,
        kanit_linki=cikti.kanit_linki,
        link_erisilebilir=link_erisilebilir,
        guven_skoru=(
            GuvenSkoruYaniti(
                kanit_orijinalligi=skor.kanit_orijinalligi,
                sonuc_olculebilirligi=skor.sonuc_olculebilirligi,
                rol_netligi=skor.rol_netligi,
                ucuncu_taraf_onayi=skor.ucuncu_taraf_onayi,
                gerekce_metni=skor.gerekce_metni,
            )
            if skor is not None
            else None
        ),
        referanslar=[
            ReferansDurumuYaniti(
                id=referans.id,
                referans_email=referans.referans_email,
                durum=referans.durum,
                puan=referans.puan,
                yanit_metni=referans.yanit_metni,
                olusturma_tarihi=referans.olusturma_tarihi,
                yanit_linki=YANIT_YOLU.format(token=referans.token),
            )
            for referans in cikti.referans_istekleri
        ],
    )
