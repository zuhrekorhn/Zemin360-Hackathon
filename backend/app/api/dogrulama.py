"""Doğrulama uç noktaları (docs/api-contracts.md § Doğrulama).

Akışlar docs/sequence-diagrams.md § Akış 2'den:
  kanıt ekle → değerlendirme + referans isteği → (yanıt | zaman aşımı) → itiraz.

Uç ince: şema, sahiplik, commit, arka plan işi ve servis istisnalarının HTTP'ye
çevrilmesi (404, 409, 429). Orkestrasyon `app/servisler/dogrulama/`'da, kurallar
`app/agents/dogrulama/`'da. Kanıt yalnızca `servisler/dogrulama/parcalar.py`
üzerinden eklenir ve kaldırılır (tek kapı).

Gösterge her değiştiğinde (kanıt, değerlendirme, itiraz, referans yanıtı) kart
sürümü artar ve commit'ten sonra kart hazırlama arka planda çalışır: uyum skoru
doğrulama bonusunu içerir, eşleşmeler de tazelenmeli (bulgu 26).

Zaman aşımı için zamanlayıcı yok: `bekliyor` → `yanit_yok` geçişi kanıt
durumu okunduğu anda hesaplanıyor (Eşleştirme'deki cron'suz yaklaşımın aynısı).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.dogrulama import GecersizReferansGecisi, yanitlanabilir_mi
from app.agents.dogrulama.kurallar import OkunanKanit
from app.api.kimlik import rol_gerekli
from app.api.sahiplik import bulunamadi, girvak_mi, yetenek_kartinin_sahibi_mi
from app.core.hatalar import HIZ_SINIRI_MESAJI
from app.core.kanit_okuma.belge import ErisimDurumu
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
    KanitLinkiIstegi,
    KanitParcasiYaniti,
    ReferansDurumuYaniti,
    ReferansIstegiGirdisi,
    ReferansIstegiYaniti,
    ReferansYanitiIstegi,
    ReferansYanitiSonucu,
    ReferansYenidenIsteIstegi,
)
from app.servisler import dogrulama as dogrulama_servisi
from app.servisler import kart_duzenleme, kart_hazirlama
from app.servisler.dogrulama import (
    CiktiBulunamadi,
    ItirazSiniri,
    KanitBulunamadi,
    KanitZatenVar,
    ReferansYenidenIstenemez,
    referans_guncel_mi,
    yeniden_isteme_engeli,
    zaman_asimini_isle,
    zaman_asimlarini_isle,
)

router = APIRouter(prefix="/dogrulama", tags=["dogrulama"])

CIKTI_BULUNAMADI = "Çalışma bulunamadı."
KANIT_BULUNAMADI = "Kanıt bulunamadı."

# Referans kişiye gönderilecek girişsiz yanıt adresi. Gerçek e-posta
# göndermiyoruz (SMTP yok, MVP kararı; adım 7'de değişir) — link API yanıtında dönüyor.
YANIT_YOLU = "/dogrulama/referans-yaniti?token={token}"


# --- Kalem (çalışma) uçları -------------------------------------------------------------


@router.get("/kalem/{somut_cikti_id}", response_model=KanitDurumuYaniti)
async def kalem_durumu(
    somut_cikti_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC, ROL_GIRVAK)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """Çalışmanın kanıtları, güven göstergesi ve referans istekleri.

    Yalnızca çalışmanın sahibi genç ve GİRVAK. Kurum 403: göstergeyi kart
    görünümünden zaten görüyor; referans e-postaları ve token'lı yanıt
    linkleri kuruma hiç gitmez (docs/faz-b-kimlik-ve-dongu.md § 3, not ²).
    Zaman aşımına uğramış referans istekleri bu okuma sırasında `yanit_yok` olur.
    """
    await _sahibinin_ciktisi(oturum, hesap, somut_cikti_id, girvak_okuyabilir=True)
    return await _durum_yaniti(oturum, somut_cikti_id, None)


@router.post("/kalem/{somut_cikti_id}/kanit", response_model=KanitDurumuYaniti, status_code=201)
async def kanit_linki_ekle(
    somut_cikti_id: uuid.UUID,
    istek: KanitLinkiIstegi,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """Link parçası ekler ve çalışmayı hemen değerlendirir. Aynı link ikinci kez 409.

    Kanıt iddiayı değiştirmez: referans yanıtları geçerli kalır (plan § 2).
    """
    cikti = await _sahibinin_ciktisi(oturum, hesap, somut_cikti_id)
    try:
        with _hiz_siniri_429():
            kontrol = await dogrulama_servisi.kanit_linki_ekle(oturum, cikti, istek.url)
    except KanitZatenVar as hata:
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    await _gosterge_degisti(oturum, cikti, arka_plan)
    return await _durum_yaniti(oturum, somut_cikti_id, _erisilebilir(kontrol))


@router.delete("/kalem/{somut_cikti_id}/kanit/{parca_id}", response_model=KanitDurumuYaniti)
async def kanit_parcasini_sil(
    somut_cikti_id: uuid.UUID,
    parca_id: uuid.UUID,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """Parçayı kaldırır; başka link kaldıysa onunla yeniden değerlendirir."""
    cikti = await _sahibinin_ciktisi(oturum, hesap, somut_cikti_id)
    try:
        with _hiz_siniri_429():
            kontrol = await dogrulama_servisi.kanit_parcasini_sil(oturum, cikti, parca_id)
    except KanitBulunamadi as hata:
        raise bulunamadi(KANIT_BULUNAMADI) from hata
    await _gosterge_degisti(oturum, cikti, arka_plan)
    return await _durum_yaniti(oturum, somut_cikti_id, _erisilebilir(kontrol))


@router.post("/kalem/{somut_cikti_id}/degerlendir", response_model=KanitDurumuYaniti)
async def degerlendir(
    somut_cikti_id: uuid.UUID,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """Çalışmayı değerlendirir (henüz değerlendirilmemiş kalem için). Linksiz çalışmada
    Sonuç ve Rol beyan tavanıyla değerlendirilir, Kanıt "—" (karar 10)."""
    cikti = await _sahibinin_ciktisi(oturum, hesap, somut_cikti_id)
    with _hiz_siniri_429():
        kontrol = await dogrulama_servisi.degerlendir(oturum, cikti)
    await _gosterge_degisti(oturum, cikti, arka_plan)
    return await _durum_yaniti(oturum, somut_cikti_id, _erisilebilir(kontrol))


@router.post("/kalem/{somut_cikti_id}/itiraz", response_model=KanitDurumuYaniti)
async def itiraz(
    somut_cikti_id: uuid.UUID,
    istek: ItirazIstegi,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """Genç değerlendirmeye itiraz eder (servis: itiraz.py). Not zorunlu; aynı not ve
    girdi önceki sonucu döndürür; sürüm başına sınır aşılınca 429."""
    cikti = await _sahibinin_ciktisi(oturum, hesap, somut_cikti_id)
    try:
        with _hiz_siniri_429():
            kontrol = await dogrulama_servisi.itiraz_et(oturum, cikti, istek.aciklama)
    except ItirazSiniri as hata:
        raise HTTPException(status_code=429, detail=str(hata)) from hata
    await _gosterge_degisti(oturum, cikti, arka_plan)
    return await _durum_yaniti(oturum, somut_cikti_id, _erisilebilir(kontrol))


@router.post("/kalem/{somut_cikti_id}/referans", response_model=KanitDurumuYaniti, status_code=201)
async def referans_iste(
    somut_cikti_id: uuid.UUID,
    istek: ReferansIstegiGirdisi,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """Referans ister. Göstergeye dokunmaz, model çağrılmaz (bulgu 16)."""
    cikti = await _sahibinin_ciktisi(oturum, hesap, somut_cikti_id)
    dogrulama_servisi.referans_iste(cikti, str(istek.referans_email))
    await dogrulama_servisi.kanit_bekleyeni_guncelle(oturum, cikti.yetenek_karti_id)
    await oturum.commit()
    return await _durum_yaniti(oturum, somut_cikti_id, None)


# --- Referans uçları --------------------------------------------------------------------


@router.post("/referans-yaniti", response_model=ReferansYanitiSonucu)
async def referans_yaniti(
    istek: ReferansYanitiIstegi,
    arka_plan: BackgroundTasks,
    oturum: AsyncSession = Depends(get_session),
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

    baslik, durum = cikti.baslik, referans.durum
    await _gosterge_degisti(oturum, cikti, arka_plan)
    return ReferansYanitiSonucu(baslik=baslik, durum=durum)


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


# --- Ortak parçalar ---------------------------------------------------------------------


@contextmanager
def _hiz_siniri_429() -> Iterator[None]:
    """Değerlendirme sırasında hız sınırı 429 olur; değişiklik kaydedilmez.

    Burada sessizce değerlendirmesiz devam etmek yanlış olurdu: genç kanıtının
    değerlendirilmediğini bilmeli.
    """
    try:
        yield
    except HizSinirHatasi as hata:
        raise HTTPException(
            status_code=429,
            detail=f"Kanıt değerlendirilemedi. {HIZ_SINIRI_MESAJI}",
        ) from hata


def _erisilebilir(okunan: OkunanKanit | None) -> bool | None:
    """Bu istekte okunan linkin içeriği okunabildi mi; link okunmadıysa None."""
    return okunan.erisim is ErisimDurumu.ACIK if okunan is not None else None


async def _gosterge_degisti(
    oturum: AsyncSession, cikti: SomutCikti, arka_plan: BackgroundTasks
) -> None:
    """Kart sürümü artar, commit, sonra kart hazırlama (yeniden eşleştirme) arka planda."""
    kart_id = cikti.yetenek_karti_id
    versiyon = await kart_duzenleme.gosterge_degisti(oturum, kart_id)
    await oturum.commit()
    arka_plan.add_task(kart_hazirlama.karti_hazirla, kart_id, versiyon)


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

    kart = await oturum.get(YetenekKarti, cikti.yetenek_karti_id)
    skor = cikti.guven_skoru
    return KanitDurumuYaniti(
        somut_cikti_id=cikti.id,
        baslik=cikti.baslik,
        kanitlar=[KanitParcasiYaniti.model_validate(p) for p in cikti.kanit_parcalari],
        link_erisilebilir=link_erisilebilir,
        guven_skoru=GuvenSkoruYaniti.model_validate(skor) if skor is not None else None,
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
                yeniden_istenebilir=yeniden_isteme_engeli(cikti, referans) is None,
            )
            for referans in cikti.referans_istekleri
        ],
        kart_kanit_bekleyen=bool(kart and kart.kanit_bekleyen),
    )
