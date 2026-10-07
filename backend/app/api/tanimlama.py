"""Tanımlama Ajanı uç noktaları (docs/api-contracts.md § Tanımlama).

Keşif ile aynı desen: sohbet durumu LangGraph checkpointer'ında, `oturum_id`
thread_id olarak kullanılıyor.

İki kapı (docs/plans/firma-akisi.md § 0 kararlar 4-5, § 5): genç yetenek
(varsayılan) ve iş birliği ortağı. Aynı motor, iki soru seti (iki grafik), tek
checkpointer; kapı sohbetin başında seçilir ve durumda (`aranan`) saklanır.
Sonraki istekler grafiği durumdan seçer; eski sohbetlerde alan yoksa genç.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.firma_karti import profil_baglami
from app.agents.sohbet_motoru import HizSinirHatasi, kullanici_mesaji
from app.agents.tanimlama import ZORUNLU_ALANLAR
from app.api.ihtiyac_kartlari import embedding_hesapla, kart_yaniti
from app.api.kimlik import rol_gerekli
from app.api.profil import kurumun_profilini_guncelle
from app.core.alan_adlari import IHTIYAC_ALAN_ADLARI, bos_alan_mesaji
from app.core.hatalar import HIZ_SINIRI_MESAJI
from app.core.ilan import ARANAN_FIRMA, ARANAN_GENC
from app.db.session import get_session
from app.models.hesap import ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.schemas.sohbet import SohbetCevapIstegi
from app.schemas.tanimlama import (
    IhtiyacKartiOnaylaIstegi,
    IhtiyacKartiYaniti,
    IhtiyacTaslagi,
    SohbetMesaji,
    TanimlamaBaslatIstegi,
    TanimlamaSohbetDurumu,
    TanimlamaSohbetYaniti,
)
from app.servisler.eslestirme import eslestirmeyi_arka_planda_calistir
from app.servisler.ilan_duzenleme import taslak_alanlari
from app.servisler.sahiplik import sohbet_baslangici, sohbetin_sahibi_mi

router = APIRouter(prefix="/tanimlama", tags=["tanimlama"])

SOHBET_BASLATILAMADI = "Sohbet şu an başlatılamadı. Biraz sonra yeniden deneyin."
SOHBET_YOK = "Bu sohbet bulunamadı. Yeni bir sohbet başlatabilirsiniz."


def _grafik(request: Request, aranan: str = ARANAN_GENC):
    ad = "tanimlama_ortak_grafigi" if aranan == ARANAN_FIRMA else "tanimlama_grafigi"
    grafik = getattr(request.app.state, ad, None)
    if grafik is None:
        raise HTTPException(status_code=503, detail=SOHBET_BASLATILAMADI)
    return grafik


def _aranan(degerler: dict) -> str:
    return degerler.get("aranan") or ARANAN_GENC


def _yanit(oturum_id: uuid.UUID, durum: dict) -> TanimlamaSohbetYaniti:
    return TanimlamaSohbetYaniti(
        oturum_id=oturum_id,
        aranan=_aranan(durum),
        soru=durum.get("sonraki_soru"),
        taslak=IhtiyacTaslagi(**(durum.get("taslak") or {})),
        taslak_hazir=bool(durum.get("taslak_hazir")),
    )


@router.post("/sohbet/baslat", response_model=TanimlamaSohbetYaniti)
async def sohbet_baslat(
    istek: TanimlamaBaslatIstegi,
    request: Request,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
) -> TanimlamaSohbetYaniti:
    oturum_id = uuid.uuid4()
    # Oturumu açan hesap checkpoint'e yazılır; cevap ve onay yalnızca ondan.
    # Firmanın kayıt bilgileri iki kapıda da sorulmaz, bağlam olarak gider (§ 5):
    # örnek sorular firmanın sektörüne uyarlanır.
    baslangic = {
        **sohbet_baslangici(hesap),
        "aranan": istek.aranan,
        "profil_baglami": profil_baglami(hesap.kurum),
    }
    durum = await _grafik(request, istek.aranan).ainvoke(
        baslangic, config={"configurable": {"thread_id": str(oturum_id)}}
    )
    return _yanit(oturum_id, durum)


def _mesajlar(durum: dict) -> list[SohbetMesaji]:
    """Checkpoint'teki mesajlar, arayüzün gösterdiği hâliyle."""
    return [
        SohbetMesaji(kim="kullanici" if mesaj.type == "human" else "ajan", metin=mesaj.content)
        for mesaj in durum.get("mesajlar") or []
        if mesaj.type in ("human", "ai") and isinstance(mesaj.content, str) and mesaj.content
    ]


@router.get("/sohbet/{oturum_id}", response_model=TanimlamaSohbetDurumu)
async def sohbet_durumu(
    oturum_id: uuid.UUID, request: Request, hesap: Hesap = Depends(rol_gerekli(ROL_KURUM))
) -> TanimlamaSohbetDurumu:
    """Sohbeti geri yükler: sayfa yenilenince firma kaldığı yerden devam eder.

    Durum zaten checkpointer'da (Postgres); arayüz yalnızca oturum kimliğini
    hatırlıyor. Başkasının ya da olmayan sohbet 404.
    """
    mevcut = await _grafik(request).aget_state({"configurable": {"thread_id": str(oturum_id)}})
    if not mevcut.values or not sohbetin_sahibi_mi(mevcut.values, hesap):
        raise HTTPException(status_code=404, detail=SOHBET_YOK)
    return TanimlamaSohbetDurumu(
        **_yanit(oturum_id, mevcut.values).model_dump(), mesajlar=_mesajlar(mevcut.values)
    )


@router.post("/sohbet/cevap", response_model=TanimlamaSohbetYaniti)
async def sohbet_cevap(
    istek: SohbetCevapIstegi, request: Request, hesap: Hesap = Depends(rol_gerekli(ROL_KURUM))
) -> TanimlamaSohbetYaniti:
    config = {"configurable": {"thread_id": str(istek.oturum_id)}}
    # İki grafik aynı checkpointer'ı paylaşıyor: durum hangisinden okunursa okunsun
    # aynı; devam edecek grafik durumdaki kapıdan seçilir.
    mevcut = await _grafik(request).aget_state(config)
    if not mevcut.values or not sohbetin_sahibi_mi(mevcut.values, hesap):
        raise HTTPException(status_code=404, detail=SOHBET_YOK)
    if mevcut.values.get("taslak_hazir"):
        raise HTTPException(status_code=409, detail="Taslağınız hazır; sıradaki adım onay.")
    grafik = _grafik(request, _aranan(mevcut.values))

    try:
        durum = await grafik.ainvoke({"mesajlar": [kullanici_mesaji(istek.cevap)]}, config=config)
    except HizSinirHatasi as hata:
        raise HTTPException(
            status_code=429,
            detail=f"{HIZ_SINIRI_MESAJI} Sohbetiniz kayıtlı.",
        ) from hata

    return _yanit(istek.oturum_id, durum)


@router.post("/kart/onayla", response_model=IhtiyacKartiYaniti, status_code=201)
async def kart_onayla(
    istek: IhtiyacKartiOnaylaIstegi,
    request: Request,
    arka_plan: BackgroundTasks,
    yanit: Response,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> IhtiyacKartiYaniti:
    """Onaylanan taslağı IHTIYAC_KARTI'na yazar, ardından embedding'ini hesaplar.

    Keşif'teki gibi tekrarlanabilir: aynı `oturum_id` ikinci kez onaylanırsa
    mevcut kart 200 ile döner, embedding'i eksikse yeniden denenir.
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
        raise HTTPException(status_code=409, detail="Taslağınız henüz hazır değil.")

    taslak = istek.duzeltilmis_taslak or IhtiyacTaslagi(**mevcut.values["taslak"])
    # Sohbet tavana gelip zorunlu alanı boş kapatmış olabilir; yer tutucu
    # yazılmıyor, firma alanı taslak ekranında doldurur.
    if bos := [alan for alan in ZORUNLU_ALANLAR if not getattr(taslak, alan)]:
        raise HTTPException(
            status_code=422, detail=bos_alan_mesaji(bos, IHTIYAC_ALAN_ADLARI, siz=True)
        )
    ortak = _aranan(mevcut.values) == ARANAN_FIRMA

    # Kart token'daki hesabın kurumuna bağlanır (docs/faz-b-kimlik-ve-dongu.md § 4).
    kurum_id = hesap.kurum.id
    kurumun_profilini_guncelle(hesap.kurum, istek.kurum_profili)

    kart = IhtiyacKarti(
        oturum_id=istek.oturum_id,
        kurum_id=kurum_id,
        aranan=ARANAN_FIRMA if ortak else ARANAN_GENC,
        **taslak_alanlari(taslak, ortak),
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
    # Voyage'a ulaşılamazsa kart kaybolmaz; eşleştirme de başlamaz, çünkü
    # embedding'siz kart aday bulamaz. Arayüz yeniden hesaplatmayı önerir.
    if await embedding_hesapla(oturum, kart):
        # Yanıt gönderildikten sonra başlıyor: kurum öneriler sayfasına
        # geldiğinde hesap çoğunlukla hazır olur.
        arka_plan.add_task(eslestirmeyi_arka_planda_calistir, kart.id)

    return await kart_yaniti(oturum, kart.id)


async def _oturumun_karti(oturum: AsyncSession, oturum_id: uuid.UUID) -> IhtiyacKarti | None:
    return await oturum.scalar(select(IhtiyacKarti).where(IhtiyacKarti.oturum_id == oturum_id))


async def _mevcut_karti_don(
    oturum: AsyncSession, kart: IhtiyacKarti, arka_plan: BackgroundTasks
) -> IhtiyacKartiYaniti:
    """Daha önce onaylanmış kartı döner; embedding'i eksikse bir kez daha dener."""
    if kart.embedding is None and await embedding_hesapla(oturum, kart):
        arka_plan.add_task(eslestirmeyi_arka_planda_calistir, kart.id)
    return await kart_yaniti(oturum, kart.id)
