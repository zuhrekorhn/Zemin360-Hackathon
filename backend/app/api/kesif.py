"""Keşif Ajanı uç noktaları (docs/api-contracts.md § Keşif).

Sohbet durumu LangGraph'ın Postgres checkpointer'ında, `oturum_id` de
thread_id olarak tutulur — uygulama tarafında ayrı bir oturum tablosu yok.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.kesif import (
    HizSinirHatasi,
    kullanici_mesaji,
    potansiyel_kurali,
    profil_baglami,
)
from app.api.kimlik import rol_gerekli
from app.api.profil import gencin_profilini_guncelle
from app.api.sahiplik import sohbet_baslangici, sohbetin_sahibi_mi
from app.api.yetenek_kartlari import embedding_hesapla, kart_yaniti
from app.core.hatalar import HIZ_SINIRI_MESAJI
from app.core.metin import gecerli_eposta
from app.db.session import get_session
from app.models.hesap import ROL_GENC, Hesap
from app.models.referans_istegi import ReferansIstegi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.kesif import (
    KartOnaylaIstegi,
    KartTaslagi,
    OnayliKart,
    SohbetBaslatIstegi,
    SohbetCevapIstegi,
    SohbetYaniti,
    SomutCiktiTaslagi,
    YetenekKartiYaniti,
)
from app.servisler import kart_hazirlama

router = APIRouter(prefix="/kesif", tags=["kesif"])

SOHBET_BASLATILAMADI = "Sohbet şu an başlatılamadı. Biraz sonra yeniden dene."
SOHBET_YOK = "Bu sohbet bulunamadı. Yeni bir sohbet başlatabilirsin."

SEHIR_GEREKLI = "Şehir gerekli: fırsatlar şehre göre eşleşiyor."
KART_EKSIK = "Kartında rol, deneyim ve en az bir sektör ilgisi olmalı."


def _grafik(request: Request):
    grafik = getattr(request.app.state, "kesif_grafigi", None)
    if grafik is None:
        # Checkpointer uygulama açılışında kuruluyor; kurulamadıysa sessizce
        # bozuk bir sohbet yürütmek yerine açıkça söyle.
        raise HTTPException(status_code=503, detail=SOHBET_BASLATILAMADI)
    return grafik


def _yanit(oturum_id: uuid.UUID, durum: dict) -> SohbetYaniti:
    return SohbetYaniti(
        oturum_id=oturum_id,
        soru=durum.get("sonraki_soru"),
        taslak=KartTaslagi(**(durum.get("taslak") or {})),
        taslak_hazir=bool(durum.get("taslak_hazir")),
    )


@router.post("/sohbet/baslat", response_model=SohbetYaniti)
async def sohbet_baslat(
    _: SohbetBaslatIstegi, request: Request, hesap: Hesap = Depends(rol_gerekli(ROL_GENC))
) -> SohbetYaniti:
    oturum_id = uuid.uuid4()
    # Oturumu açan hesap checkpoint'e yazılır; cevap ve onay yalnızca ondan.
    # Kayıt formundan bilinenler bağlam olarak gider ve sorulmaz (plan § 5.3).
    baslangic = {**sohbet_baslangici(hesap), "profil_baglami": profil_baglami(hesap.kullanici)}
    durum = await _grafik(request).ainvoke(
        baslangic, config={"configurable": {"thread_id": str(oturum_id)}}
    )
    return _yanit(oturum_id, durum)


@router.post("/sohbet/cevap", response_model=SohbetYaniti)
async def sohbet_cevap(
    istek: SohbetCevapIstegi, request: Request, hesap: Hesap = Depends(rol_gerekli(ROL_GENC))
) -> SohbetYaniti:
    config = {"configurable": {"thread_id": str(istek.oturum_id)}}
    grafik = _grafik(request)

    mevcut = await grafik.aget_state(config)
    if not mevcut.values or not sohbetin_sahibi_mi(mevcut.values, hesap):
        raise HTTPException(status_code=404, detail=SOHBET_YOK)
    if mevcut.values.get("taslak_hazir"):
        raise HTTPException(status_code=409, detail="Taslağın hazır; sıradaki adım onay.")

    try:
        durum = await grafik.ainvoke({"mesajlar": [kullanici_mesaji(istek.cevap)]}, config=config)
    except HizSinirHatasi as hata:
        # Sohbet durumu checkpointer'da duruyor; kullanıcı biraz sonra aynı
        # oturum_id ile kaldığı yerden devam edebilir.
        raise HTTPException(
            status_code=429,
            detail=f"{HIZ_SINIRI_MESAJI} Sohbetin kayıtlı.",
        ) from hata

    return _yanit(istek.oturum_id, durum)


@router.post("/kart/onayla", response_model=YetenekKartiYaniti, status_code=201)
async def kart_onayla(
    istek: KartOnaylaIstegi,
    request: Request,
    yanit: Response,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> YetenekKartiYaniti:
    """Onaylanan taslağı YETENEK_KARTI'na yazar, ardından embedding'ini hesaplar.

    Tekrarlanabilir: aynı `oturum_id` ikinci kez onaylanırsa (çift tıklama,
    embedding hatası sonrası yeniden deneme) yeni kart açılmaz, mevcut kart
    200 ile döner — embedding'i eksikse bu sırada yeniden denenir.

    Yanıttan sonra kart hazırlanır (app/servisler/kart_hazirlama.py): linkli iş
    kalemleri puanlanır, kart mevcut ihtiyaç kartlarıyla eşleştirilir. Tekrarda
    da sıraya girer; iş idempotent.
    """
    config = {"configurable": {"thread_id": str(istek.oturum_id)}}
    mevcut = await _grafik(request).aget_state(config)
    if not mevcut.values or not sohbetin_sahibi_mi(mevcut.values, hesap):
        raise HTTPException(status_code=404, detail=SOHBET_YOK)

    onceki = await _oturumun_karti(oturum, istek.oturum_id)
    if onceki is not None:
        yanit.status_code = 200
        return await _mevcut_karti_don(oturum, onceki, arka_plan)

    if not mevcut.values.get("taslak_hazir"):
        raise HTTPException(status_code=409, detail="Taslağın henüz hazır değil.")

    taslak = istek.duzeltilmis_taslak or KartTaslagi(**mevcut.values["taslak"])
    # Kullanıcı taslak ekranında tüm çıktıları çıkarmış olabilir: sohbetin
    # kapatırken uyguladığı kural burada da işlesin (agent-specs.md § 1.4).
    taslak = taslak.model_copy(
        update={
            "deneyim_seviyesi": potansiyel_kurali(
                taslak.deneyim_seviyesi, len(taslak.somut_ciktilar)
            )
        }
    )
    try:
        onayli = OnayliKart.model_validate(taslak.model_dump())
    except ValidationError as hata:
        raise HTTPException(status_code=422, detail=KART_EKSIK) from hata

    # Kart token'daki hesabın profiline bağlanır; onay yalnızca eşleştirmeyi
    # etkileyen alanları günceller (docs/faz-b-kimlik-ve-dongu.md § 4).
    kullanici = hesap.kullanici
    gencin_profilini_guncelle(kullanici, istek.profil)
    if not kullanici.sehir:
        raise HTTPException(status_code=422, detail=SEHIR_GEREKLI)

    kart = YetenekKarti(
        oturum_id=istek.oturum_id,
        kullanici_id=kullanici.id,
        rol_alani=onayli.rol_alani,
        deneyim_seviyesi=onayli.deneyim_seviyesi,
        sektor_ilgi_alani=onayli.sektor_ilgi_alani,
        araclar_teknolojiler=taslak.araclar_teknolojiler,
        sertifikalar=taslak.sertifikalar,
        diller=taslak.diller,
        # Kanıt linki olmayan bir çıktı varsa kart "kanıt bekleyen" sayılır.
        kanit_bekleyen=any(not c.kanit_linki for c in taslak.somut_ciktilar),
        somut_ciktilar=[_is_kalemi(c) for c in taslak.somut_ciktilar],
    )
    oturum.add(kart)
    try:
        await oturum.commit()
    except IntegrityError:
        # Aynı oturum için eşzamanlı ikinci onay: diğer istek kartı yazdı.
        await oturum.rollback()
        onceki = await _oturumun_karti(oturum, istek.oturum_id)
        if onceki is None:
            raise
        yanit.status_code = 200
        return await _mevcut_karti_don(oturum, onceki, arka_plan)

    # Kart kaydedildikten SONRA embedding (docs/matching-algorithm.md § 1-2).
    # Voyage'a ulaşılamazsa kart kaybolmaz: embedding NULL kalır, yanıtta
    # `embedding_var: false` döner ve arayüz yeniden hesaplatmayı önerir.
    await embedding_hesapla(oturum, kart)
    arka_plan.add_task(kart_hazirlama.karti_hazirla, kart.id, kart.versiyon)

    return await kart_yaniti(oturum, kart.id)


def _is_kalemi(taslak: SomutCiktiTaslagi) -> SomutCikti:
    """Taslaktaki iş kalemi; referans e-postası iş kalemine referans isteği olur.

    Geçersiz e-posta sessizce atılır: sohbetten çıkarılan bir değer onayı
    düşürmemeli; genç kart sayfasından referans ekleyebilir.
    """
    cikti = SomutCikti(
        baslik=taslak.baslik,
        aciklama=taslak.aciklama,
        kanit_linki=taslak.kanit_linki,
        is_turu=taslak.is_turu,
        olculebilir_sonuc=taslak.olculebilir_sonuc,
        kendi_rolu=taslak.kendi_rolu,
    )
    eposta = gecerli_eposta(taslak.referans_email)
    if eposta:
        cikti.referans_istekleri.append(ReferansIstegi(referans_email=eposta))
    return cikti


async def _oturumun_karti(oturum: AsyncSession, oturum_id: uuid.UUID) -> YetenekKarti | None:
    return await oturum.scalar(
        select(YetenekKarti)
        .options(selectinload(YetenekKarti.somut_ciktilar))
        .where(YetenekKarti.oturum_id == oturum_id)
    )


async def _mevcut_karti_don(
    oturum: AsyncSession, kart: YetenekKarti, arka_plan: BackgroundTasks
) -> YetenekKartiYaniti:
    """Daha önce onaylanmış kartı döner; embedding'i eksikse bir kez daha dener."""
    if kart.embedding is None:
        await embedding_hesapla(oturum, kart)
    arka_plan.add_task(kart_hazirlama.karti_hazirla, kart.id, kart.versiyon)
    return await kart_yaniti(oturum, kart.id)
