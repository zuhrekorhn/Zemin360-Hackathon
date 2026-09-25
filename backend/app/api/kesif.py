"""Keşif Ajanı uç noktaları (docs/api-contracts.md § Keşif).

Sohbet durumu LangGraph'ın Postgres checkpointer'ında, `oturum_id` de
thread_id olarak tutulur — uygulama tarafında ayrı bir oturum tablosu yok.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import Insert, case, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.kesif import HizSinirHatasi, kullanici_mesaji, potansiyel_kurali
from app.api.kimlik import rol_gerekli
from app.api.sahiplik import sohbet_baslangici, sohbetin_sahibi_mi
from app.api.yetenek_kartlari import embedding_hesapla, kart_yaniti
from app.core import calisma_modeli
from app.core.hatalar import HIZ_SINIRI_MESAJI
from app.core.metin import eposta_normalize
from app.core.sehir import sehir_kanonik
from app.db.session import get_session
from app.models.hesap import ROL_GENC, Hesap
from app.models.kullanici import Kullanici
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.kesif import (
    KartOnaylaIstegi,
    KartTaslagi,
    SohbetBaslatIstegi,
    SohbetCevapIstegi,
    SohbetYaniti,
    YetenekKartiYaniti,
)

router = APIRouter(prefix="/kesif", tags=["kesif"])


def _grafik(request: Request):
    grafik = getattr(request.app.state, "kesif_grafigi", None)
    if grafik is None:
        # Checkpointer uygulama açılışında kuruluyor; kurulamadıysa sessizce
        # bozuk bir sohbet yürütmek yerine açıkça söyle.
        raise HTTPException(status_code=503, detail="Keşif Ajanı hazır değil")
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
    durum = await _grafik(request).ainvoke(
        sohbet_baslangici(hesap), config={"configurable": {"thread_id": str(oturum_id)}}
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
        raise HTTPException(status_code=404, detail="Sohbet oturumu bulunamadı")
    if mevcut.values.get("taslak_hazir"):
        raise HTTPException(status_code=409, detail="Taslak hazır; sıradaki adım onay")

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
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> YetenekKartiYaniti:
    """Onaylanan taslağı YETENEK_KARTI'na yazar, ardından embedding'ini hesaplar.

    Tekrarlanabilir: aynı `oturum_id` ikinci kez onaylanırsa (çift tıklama,
    embedding hatası sonrası yeniden deneme) yeni kart açılmaz, mevcut kart
    200 ile döner — embedding'i eksikse bu sırada yeniden denenir.
    """
    config = {"configurable": {"thread_id": str(istek.oturum_id)}}
    mevcut = await _grafik(request).aget_state(config)
    if not mevcut.values or not sohbetin_sahibi_mi(mevcut.values, hesap):
        raise HTTPException(status_code=404, detail="Sohbet oturumu bulunamadı")

    onceki = await _oturumun_karti(oturum, istek.oturum_id)
    if onceki is not None:
        yanit.status_code = 200
        return await _mevcut_karti_don(oturum, onceki)

    if not mevcut.values.get("taslak_hazir"):
        raise HTTPException(status_code=409, detail="Taslak henüz hazır değil")

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
    if not taslak.rol_alani or not taslak.deneyim_seviyesi:
        raise HTTPException(status_code=422, detail="Taslakta rol ve deneyim seviyesi zorunlu")

    kullanici_id = await _kullaniciyi_kaydet(oturum, istek)

    kart = YetenekKarti(
        oturum_id=istek.oturum_id,
        kullanici_id=kullanici_id,
        rol_alani=taslak.rol_alani,
        deneyim_seviyesi=taslak.deneyim_seviyesi,
        sektor_ilgi_alani=taslak.sektor_ilgi_alani,
        araclar_teknolojiler=taslak.araclar_teknolojiler,
        # Kanıt linki olmayan bir çıktı varsa kart "kanıt bekleyen" sayılır;
        # Doğrulama Ajanı bunları Faz 2'de ele alacak.
        kanit_bekleyen=any(not c.kanit_linki for c in taslak.somut_ciktilar),
        somut_ciktilar=[
            SomutCikti(baslik=c.baslik, aciklama=c.aciklama, kanit_linki=c.kanit_linki)
            for c in taslak.somut_ciktilar
        ],
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
        return await _mevcut_karti_don(oturum, onceki)

    # Kart kaydedildikten SONRA embedding (docs/matching-algorithm.md § 1-2).
    # Voyage'a ulaşılamazsa kart kaybolmaz: embedding NULL kalır, yanıtta
    # `embedding_var: false` döner ve arayüz yeniden hesaplatmayı önerir.
    await embedding_hesapla(oturum, kart)

    return await kart_yaniti(oturum, kart.id)


async def _oturumun_karti(oturum: AsyncSession, oturum_id: uuid.UUID) -> YetenekKarti | None:
    return await oturum.scalar(
        select(YetenekKarti)
        .options(selectinload(YetenekKarti.somut_ciktilar))
        .where(YetenekKarti.oturum_id == oturum_id)
    )


async def _mevcut_karti_don(oturum: AsyncSession, kart: YetenekKarti) -> YetenekKartiYaniti:
    """Daha önce onaylanmış kartı döner; embedding'i eksikse bir kez daha dener."""
    if kart.embedding is None:
        await embedding_hesapla(oturum, kart)
    return await kart_yaniti(oturum, kart.id)


def kullanici_upsert_ifadesi(
    *,
    ad: str,
    email: str,
    sehir: str | None,
    calisma_modelleri: list[str],
    musaitlik: str | None,
) -> Insert:
    """Kullanıcıyı e-postasıyla ekler ya da günceller; kimliğini döner.

    Tek ifade, yarışa dayanıklı (email UNIQUE). Kayıtlı kişi onayda yeni
    bilgi verdiyse güncellenir — eskiden yok sayılıyordu, ikinci kartında
    şehrini değiştiren gencin filtresi eski şehre göre çalışıyordu.

    Boş gelen alan kayıtlı değeri SİLMEZ (taslak birleştirmedeki kuralın
    aynısı): skalerlerde COALESCE, listede "boşsa eskisi kalsın".

    Bu "e-postayla bul" mantığı Faz B'de hesaba bağlanınca kalkacak.
    """
    ifade = pg_insert(Kullanici).values(
        id=uuid.uuid4(),
        ad=ad,
        email=email,
        sehir=sehir,
        calisma_modelleri=calisma_modelleri,
        musaitlik=musaitlik,
    )
    yeni, eski = ifade.excluded, Kullanici.__table__.c
    return ifade.on_conflict_do_update(
        index_elements=[Kullanici.email],
        set_={
            "ad": func.coalesce(yeni.ad, eski.ad),
            "sehir": func.coalesce(yeni.sehir, eski.sehir),
            "musaitlik": func.coalesce(yeni.musaitlik, eski.musaitlik),
            "calisma_modelleri": case(
                (func.cardinality(yeni.calisma_modelleri) == 0, eski.calisma_modelleri),
                else_=yeni.calisma_modelleri,
            ),
        },
    ).returning(Kullanici.id)


async def _kullaniciyi_kaydet(oturum: AsyncSession, istek: KartOnaylaIstegi) -> uuid.UUID:
    girdi = istek.kullanici
    return await oturum.scalar(
        kullanici_upsert_ifadesi(
            ad=girdi.ad,
            email=eposta_normalize(str(girdi.email)),
            sehir=sehir_kanonik(girdi.sehir),
            calisma_modelleri=calisma_modeli.temizle(girdi.calisma_modelleri),
            musaitlik=girdi.musaitlik,
        )
    )
