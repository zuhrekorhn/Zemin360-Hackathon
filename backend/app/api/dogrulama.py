"""Doğrulama uç noktaları (docs/api-contracts.md § Doğrulama).

Akışlar docs/sequence-diagrams.md § Akış 2'den:
  kanıt ekle → ön rubrik + referans isteği → (yanıt | zaman aşımı) → itiraz.

Uç ince: şema, sahiplik, commit ve servis istisnalarının HTTP'ye çevrilmesi
(404, 409, 429). Orkestrasyon `app/servisler/dogrulama/`'da, kurallar
`app/agents/dogrulama/`'da.

Zaman aşımı için zamanlayıcı yok: `bekliyor` → `yanit_yok` geçişi kanıt
durumu okunduğu anda hesaplanıyor (Eşleştirme'deki cron'suz yaklaşımın aynısı).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.dogrulama import GecersizReferansGecisi, yanitlanabilir_mi
from app.api.kimlik import rol_gerekli
from app.api.sahiplik import bulunamadi, girvak_mi, yetenek_kartinin_sahibi_mi
from app.core.hatalar import HIZ_SINIRI_MESAJI
from app.core.llm import HizSinirHatasi
from app.db.session import get_session
from app.models.hesap import ROL_GENC, ROL_GIRVAK, Hesap
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
    ReferansYanitiSonucu,
    ReferansYenidenIsteIstegi,
)
from app.servisler import dogrulama as dogrulama_servisi
from app.servisler.dogrulama import (
    CiktiBulunamadi,
    ReferansYenidenIstenemez,
    referans_guncel_mi,
    zaman_asimini_isle,
    zaman_asimlarini_isle,
)

router = APIRouter(prefix="/dogrulama", tags=["dogrulama"])

CIKTI_BULUNAMADI = "Çalışma bulunamadı."

# Referans kişiye gönderilecek girişsiz yanıt adresi. Gerçek e-posta
# göndermiyoruz (SMTP yok, MVP kararı) — link API yanıtında dönüyor.
YANIT_YOLU = "/dogrulama/referans-yaniti?token={token}"


@router.post("/kanit-ekle", response_model=KanitDurumuYaniti, status_code=201)
async def kanit_ekle(
    istek: KanitEkleIstegi,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """Kanıtı kaydeder, erişilebilirliğini sınar, ön rubrik puanını üretir.

    Yalnızca çıktının sahibi genç; başkasının çıktısı 404.
    """
    cikti = await _sahibinin_ciktisi(oturum, hesap, istek.somut_cikti_id)
    with _hiz_siniri_429():
        kontrol = await dogrulama_servisi.kanit_ekle(
            oturum,
            cikti,
            kanit_linki=istek.kanit_linki,
            kanit_turu=istek.kanit_turu,
            referans_email=str(istek.referans_email) if istek.referans_email else None,
        )
    await oturum.commit()
    return await _durum_yaniti(oturum, cikti.id, kontrol.erisilebilir)


@router.post("/referans-yaniti", response_model=ReferansYanitiSonucu)
async def referans_yaniti(
    istek: ReferansYanitiIstegi, oturum: AsyncSession = Depends(get_session)
) -> ReferansYanitiSonucu:
    """Token ile bulunur, giriş gerektirmez (api-contracts.md § Mimari Notlar).

    Yanıt yalnızca iddianın başlığını ve durumu taşır: bu uç noktayı tek
    bir token'ı olan herkes çağırabiliyor, kanıtın geri kalanı (diğer
    referanslar, puanlar, token'lar) onun işi değil.
    """
    referans = await oturum.scalar(
        select(ReferansIstegi).where(ReferansIstegi.token == istek.token)
    )
    if referans is None:
        raise HTTPException(status_code=404, detail="Referans isteği bulunamadı")

    # Zaman aşımı burada da uygulanıyor: GET "yanıtlanamaz" derken POST'un
    # yanıtı kabul etmesi, iki uç noktanın farklı kural işletmesi olurdu.
    if zaman_asimini_isle(referans):
        await oturum.commit()
    try:
        cikti = await dogrulama_servisi.referans_yanitla(
            oturum, referans, puan=istek.puan, yorum=istek.yorum
        )
    except GecersizReferansGecisi as hata:
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    except CiktiBulunamadi as hata:
        raise bulunamadi(CIKTI_BULUNAMADI) from hata

    await oturum.commit()
    return ReferansYanitiSonucu(baslik=cikti.baslik, durum=referans.durum)


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

    if zaman_asimini_isle(referans):
        await oturum.commit()

    return referans_gorunumu(referans)


@router.get("/kanit/{somut_cikti_id}", response_model=KanitDurumuYaniti)
async def kanit_durumu(
    somut_cikti_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC, ROL_GIRVAK)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """Kanıtın güncel durumu: rubrik ve referans istekleri (e-postalar, yanıt linkleri).

    Yalnızca çıktının sahibi genç ve GİRVAK. Kurum 403: rubriği yetenek kartı
    görünümünden zaten görüyor; referans e-postaları ve token'lı yanıt
    linkleri kuruma hiç gitmez (docs/faz-b-kimlik-ve-dongu.md § 3, not ²).

    Zaman aşımına uğramış referans istekleri bu okuma sırasında `yanit_yok`
    olarak işaretlenir — ayrı bir zamanlayıcı kurmuyoruz (bilinçli).
    """
    await _sahibinin_ciktisi(oturum, hesap, somut_cikti_id, girvak_okuyabilir=True)
    return await _durum_yaniti(oturum, somut_cikti_id, None)


@router.post("/itiraz", response_model=KanitDurumuYaniti)
async def itiraz(
    istek: ItirazIstegi,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """Genç değerlendirmeye itiraz eder; rubrik yeniden hesaplanır (servis: itiraz.py)."""
    cikti = await _sahibinin_ciktisi(oturum, hesap, istek.somut_cikti_id)
    with _hiz_siniri_429():
        kontrol = await dogrulama_servisi.itiraz_et(
            oturum, cikti, yeni_kanit_linki=istek.yeni_kanit_linki, aciklama=istek.aciklama
        )
    await oturum.commit()
    return await _durum_yaniti(oturum, cikti.id, kontrol.erisilebilir)


@router.post("/referans-yeniden-iste", response_model=KanitDurumuYaniti, status_code=201)
async def referans_yeniden_iste(
    istek: ReferansYenidenIsteIstegi,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """Aynı kişiye yeni bir istek açar (yeni token); eski yanıt geçmiş olarak kalır.

    İş kalemi değişince eski yanıt puana girmiyor (plan § 0, karar 8); genç
    referansı işin güncel hâli için yeniden isteyebilir. Yalnızca kalemin sahibi.
    Rubrik yeniden çalışmaz: yalnızca referans isteği açılır.
    """
    referans = await oturum.get(ReferansIstegi, istek.referans_id)
    if referans is None:
        raise bulunamadi("Referans isteği bulunamadı")
    cikti = await _sahibinin_ciktisi(oturum, hesap, referans.somut_cikti_id)
    try:
        dogrulama_servisi.referansi_yeniden_iste(cikti, referans)
    except ReferansYenidenIstenemez as hata:
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    await oturum.commit()
    return await _durum_yaniti(oturum, cikti.id, None)


# --- Ortak parçalar --------------------------------------------------------


@contextmanager
def _hiz_siniri_429() -> Iterator[None]:
    """Rubrik yazılırken hız sınırı 429 olur.

    Burada sessizce puansız devam etmek yanlış olurdu: kullanıcı kanıtının
    değerlendirilmediğini bilmeli.
    """
    try:
        yield
    except HizSinirHatasi as hata:
        raise HTTPException(
            status_code=429,
            detail=f"Kanıt değerlendirilemedi. {HIZ_SINIRI_MESAJI}",
        ) from hata


def referans_gorunumu(referans: ReferansIstegi) -> ReferansIstegiYaniti:
    """Referans isteğini, girişsiz sayfaya açılabilecek alanlara indirger."""
    cikti = referans.somut_cikti
    return ReferansIstegiYaniti(
        somut_cikti_id=cikti.id,
        baslik=cikti.baslik,
        aciklama=cikti.aciklama,
        iddia_sahibi_adi=cikti.yetenek_karti.kullanici.ad,
        durum=referans.durum,
        yanitlanabilir=yanitlanabilir_mi(referans.durum),
    )


async def _sahibinin_ciktisi(
    oturum: AsyncSession,
    hesap: Hesap,
    somut_cikti_id: uuid.UUID,
    girvak_okuyabilir: bool = False,
) -> SomutCikti:
    """Çıktıyı getirir; hesap çıktının kartının sahibi değilse 404."""
    cikti = await _ciktiyi_getir(oturum, somut_cikti_id)
    kart = await oturum.get(YetenekKarti, cikti.yetenek_karti_id)
    izinli = yetenek_kartinin_sahibi_mi(hesap, kart) or (girvak_okuyabilir and girvak_mi(hesap))
    if not izinli:
        raise bulunamadi(CIKTI_BULUNAMADI)
    return cikti


async def _ciktiyi_getir(oturum: AsyncSession, somut_cikti_id: uuid.UUID) -> SomutCikti:
    try:
        return await dogrulama_servisi.cikti_getir(oturum, somut_cikti_id)
    except CiktiBulunamadi as hata:
        raise bulunamadi(CIKTI_BULUNAMADI) from hata


async def _durum_yaniti(
    oturum: AsyncSession, somut_cikti_id: uuid.UUID, link_erisilebilir: bool | None
) -> KanitDurumuYaniti:
    cikti = await _ciktiyi_getir(oturum, somut_cikti_id)

    # Zaman aşımı: okuma anında hesaplanıp kalıcılaştırılır.
    if zaman_asimlarini_isle(cikti.referans_istekleri):
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
                guncel=referans_guncel_mi(cikti, referans),
            )
            for referans in cikti.referans_istekleri
        ],
    )
