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
durumu okunduğu anda ve Canlılık taramasında hesaplanıyor (cron'suz yaklaşım).

Referans e-postası referansa doğrudan gider (yanıttan sonra, arka planda); yanıt
linki ve token hiçbir yanıtta dönmez (bulgu 31).
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.dogrulama import (
    DURUM_BEKLIYOR,
    GecersizReferansGecisi,
    eposta_gucu,
    yanitlanabilir_mi,
)
from app.agents.dogrulama.kurallar import OkunanKanit
from app.api.kimlik import rol_gerekli
from app.api.sahiplik import bulunamadi, girvak_mi, yetenek_kartinin_sahibi_mi
from app.core import istek_izi
from app.core.dis_servisler.depo import DepoKapali
from app.core.dis_servisler.eposta import Eposta
from app.core.dosya_hatti import AZAMI_BOYUT, MB, DosyaReddedildi
from app.core.hatalar import HIZ_SINIRI_MESAJI
from app.core.kanit_okuma.belge import ErisimDurumu
from app.core.llm import HizSinirHatasi
from app.db.session import get_session
from app.models.hesap import ROL_GENC, ROL_GIRVAK, Hesap
from app.models.referans_istegi import ReferansIstegi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.dogrulama import (
    DosyaGorunurlukIstegi,
    GuvenSkoruYaniti,
    IndirmeAdresiYaniti,
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
from app.servisler import inceleme, kart_duzenleme, kart_hazirlama
from app.servisler.dogrulama import (
    CiktiBulunamadi,
    FormYaniti,
    ItirazIncelemede,
    KanitBulunamadi,
    KanitZatenVar,
    KendiReferansi,
    ReferansYenidenIstenemez,
    ReferansZatenBekliyor,
    dosyalar,
    referans_guncel_mi,
    yeniden_isteme_engeli,
    zaman_asimini_isle,
    zaman_asimlarini_isle,
)
from app.servisler.dogrulama.isaretler.referans_suphesi import form_acildi
from app.servisler.dogrulama.parcalar import DosyaSiniri
from app.servisler.dogrulama.referans_epostasi import epostalari_gonder

router = APIRouter(prefix="/dogrulama", tags=["dogrulama"])

CIKTI_BULUNAMADI = "Çalışma bulunamadı."
KANIT_BULUNAMADI = "Kanıt bulunamadı."
REFERANS_BULUNAMADI = "Referans isteği bulunamadı"


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
        anahtarlar = dosyalar.dosya_anahtarlari([dogrulama_servisi.parca_bul(cikti, parca_id)])
        with _hiz_siniri_429():
            kontrol = await dogrulama_servisi.kanit_parcasini_sil(oturum, cikti, parca_id)
    except KanitBulunamadi as hata:
        raise bulunamadi(KANIT_BULUNAMADI) from hata
    await _gosterge_degisti(oturum, cikti, arka_plan)
    # Dosya depodan commit'ten sonra silinir (işlem düşerse satır da dosya da kalır).
    arka_plan.add_task(dosyalar.depodan_sil, anahtarlar)
    return await _durum_yaniti(oturum, somut_cikti_id, _erisilebilir(kontrol))


DOSYA_KAPALI = "Dosya yükleme şu an kapalı; kanıtını link ya da referansla ekleyebilirsin."


@router.post("/kalem/{somut_cikti_id}/dosya", response_model=KanitDurumuYaniti, status_code=201)
async def kanit_dosyasi_ekle(
    somut_cikti_id: uuid.UUID,
    arka_plan: BackgroundTasks,
    dosya: UploadFile = File(...),
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """PDF ya da görsel ekler (plan § 4): güvenli hale getirilir, depoya konur, çalışma
    hemen değerlendirilir. Kabul edilmeyen dosya 422, aynı dosya 409, depo kapalı 503."""
    cikti = await _sahibinin_ciktisi(oturum, hesap, somut_cikti_id)
    ham = await dosya.read(AZAMI_BOYUT + 1)
    if len(ham) > AZAMI_BOYUT:
        raise HTTPException(
            status_code=422,
            detail=f"Bu dosya çok büyük; en çok {AZAMI_BOYUT // MB} MB yükleyebilirsin.",
        )
    kart = await oturum.get(YetenekKarti, cikti.yetenek_karti_id)
    try:
        with _hiz_siniri_429():
            kontrol = await dosyalar.dosya_ekle(
                oturum, cikti, kart.kullanici_id, ham, dosya.filename
            )
    except (DosyaReddedildi, DosyaSiniri) as hata:
        raise HTTPException(status_code=422, detail=str(hata)) from hata
    except KanitZatenVar as hata:
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    except DepoKapali as hata:
        raise HTTPException(status_code=503, detail=DOSYA_KAPALI) from hata
    await _gosterge_degisti(oturum, cikti, arka_plan)
    return await _durum_yaniti(oturum, somut_cikti_id, _erisilebilir(kontrol))


@router.get("/kalem/{somut_cikti_id}/kanit/{parca_id}/indir", response_model=IndirmeAdresiYaniti)
async def kanit_dosyasini_indir(
    somut_cikti_id: uuid.UUID,
    parca_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC, ROL_GIRVAK)),
    oturum: AsyncSession = Depends(get_session),
) -> IndirmeAdresiYaniti:
    """Dosyanın birkaç dakika geçerli indirme adresi. Genç ve GİRVAK; firma kart
    görünümünden ve yalnızca gencin açtığı dosyalar için (`yetenek_kartlari`)."""
    cikti = await _sahibinin_ciktisi(oturum, hesap, somut_cikti_id, girvak_okuyabilir=True)
    try:
        return IndirmeAdresiYaniti(adres=await dosyalar.indirme_adresi(cikti, parca_id))
    except KanitBulunamadi as hata:
        raise bulunamadi(KANIT_BULUNAMADI) from hata
    except DepoKapali as hata:
        raise HTTPException(status_code=503, detail=DOSYA_KAPALI) from hata


@router.patch("/kalem/{somut_cikti_id}/kanit/{parca_id}", response_model=KanitDurumuYaniti)
async def dosya_gorunurlugu(
    somut_cikti_id: uuid.UUID,
    parca_id: uuid.UUID,
    istek: DosyaGorunurlukIstegi,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """ "Firmalar görebilir" seçeneği. Gösterge ve kart sürümü değişmez."""
    cikti = await _sahibinin_ciktisi(oturum, hesap, somut_cikti_id)
    try:
        dosyalar.gorunurlugu_degistir(cikti, parca_id, istek.gorunur_firmaya)
    except KanitBulunamadi as hata:
        raise bulunamadi(KANIT_BULUNAMADI) from hata
    await oturum.commit()
    return await _durum_yaniti(oturum, somut_cikti_id, None)


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
    yanit: Response,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """Genç değerlendirmeye itiraz eder (servis: itiraz.py). Not zorunlu; aynı not ve
    girdi önceki sonucu döndürür. Sürüm başına sınır aşılınca model çağrılmaz, itiraz
    GİRVAK kuyruğuna gider: 202 ve `inceleme_bekliyor: true`, gösterge değişmez."""
    cikti = await _sahibinin_ciktisi(oturum, hesap, somut_cikti_id)
    try:
        with _hiz_siniri_429():
            kontrol = await dogrulama_servisi.itiraz_et(oturum, cikti, istek.aciklama)
    except ItirazIncelemede:
        await oturum.commit()
        yanit.status_code = 202
        return await _durum_yaniti(oturum, somut_cikti_id, None)
    await _gosterge_degisti(oturum, cikti, arka_plan)
    return await _durum_yaniti(oturum, somut_cikti_id, _erisilebilir(kontrol))


@router.post("/kalem/{somut_cikti_id}/referans", response_model=KanitDurumuYaniti, status_code=201)
async def referans_iste(
    somut_cikti_id: uuid.UUID,
    istek: ReferansIstegiGirdisi,
    request: Request,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """Referans ister; e-posta yanıttan sonra referansa gider. Göstergeye dokunmaz,
    model çağrılmaz (bulgu 16). Gencin kendi adresi 422, aynı kişiden bekleyen istek 409."""
    cikti = await _sahibinin_ciktisi(oturum, hesap, somut_cikti_id)
    try:
        eposta = await dogrulama_servisi.referans_iste(
            oturum, cikti, str(istek.referans_email), hesap.email, istek_izi.istekten(request)
        )
    except KendiReferansi as hata:
        raise HTTPException(status_code=422, detail=str(hata)) from hata
    except ReferansZatenBekliyor as hata:
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    await dogrulama_servisi.kanit_bekleyeni_guncelle(oturum, cikti.yetenek_karti_id)
    await oturum.commit()
    _eposta_gonder(arka_plan, eposta)
    return await _durum_yaniti(oturum, somut_cikti_id, None)


# --- Referans uçları --------------------------------------------------------------------


@router.post("/referans-yaniti", response_model=ReferansYanitiSonucu)
async def referans_yaniti(
    istek: ReferansYanitiIstegi,
    request: Request,
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
        raise HTTPException(status_code=404, detail=REFERANS_BULUNAMADI)

    # Zaman aşımı burada da uygulanıyor: GET "yanıtlanamaz" derken POST'un
    # yanıtı kabul etmesi, iki uç noktanın farklı kural işletmesi olurdu.
    if await zaman_asimini_isle(oturum, referans):
        await oturum.commit()
    try:
        sonuc = await dogrulama_servisi.referans_yanitla(
            oturum,
            referans,
            FormYaniti(
                iliski=istek.iliski,
                iddia=istek.iddia_dogru,
                pay=istek.pay_dogru,
                sonuc=istek.sonuc_dogru,
                yorum=(istek.yorum or "").strip() or None,
            ),
            istek_izi.istekten(request),
        )
    except GecersizReferansGecisi as hata:
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    except CiktiBulunamadi as hata:
        raise bulunamadi(CIKTI_BULUNAMADI) from hata

    cikti = sonuc.cikti
    baslik, durum = cikti.baslik, referans.durum
    # Sonuç / Rol desteği değiştiyse kalem arka planda yeniden puanlanır (plan § 7).
    await _gosterge_degisti(oturum, cikti, arka_plan, yeniden_puanla=sonuc.destek_degisti)
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

    zaman_asimi = await zaman_asimini_isle(oturum, referans)
    # Formun ilk açılışı: yanıt süresi buradan ölçülür (referans_supheli).
    if form_acildi(referans, dt.datetime.now(dt.UTC)) or zaman_asimi:
        await oturum.commit()

    return referans_gorunumu(referans)


@router.post("/referans-yeniden-iste", response_model=KanitDurumuYaniti, status_code=201)
async def referans_yeniden_iste(
    istek: ReferansYenidenIsteIstegi,
    request: Request,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """Aynı kişiye yeni bir istek açar (yeni token); eski yanıt geçmiş olarak kalır.

    İş kalemi değişince eski yanıt puana girmiyor (plan § 0, karar 8); genç
    referansı işin güncel hâli için yeniden isteyebilir. Yalnızca kalemin sahibi.
    Rubrik yeniden çalışmaz: yalnızca referans isteği açılır.
    """
    cikti, referans = await _sahibinin_referansi(oturum, hesap, istek.referans_id)
    try:
        eposta = await dogrulama_servisi.referansi_yeniden_iste(
            oturum, cikti, referans, istek_izi.istekten(request)
        )
    except ReferansYenidenIstenemez as hata:
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    await oturum.commit()
    _eposta_gonder(arka_plan, eposta)
    return await _durum_yaniti(oturum, cikti.id, None)


@router.post("/referans/{referans_id}/geri-cek", response_model=KanitDurumuYaniti)
async def referans_geri_cek(
    referans_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> KanitDurumuYaniti:
    """Bekleyen isteği geri çeker (ör. yanlış adres); link artık form açmaz.

    Tekrarı 200 ve yan etkisiz; yanıtlanmış ya da süresi dolmuş istek 409.
    Yalnızca kalemin sahibi; başkasının isteği 404.
    """
    cikti, referans = await _sahibinin_referansi(oturum, hesap, referans_id)
    try:
        await dogrulama_servisi.referansi_geri_cek(oturum, referans)
    except GecersizReferansGecisi as hata:
        await oturum.commit()  # okuma anındaki zaman aşımı geçişi kalıcı olsun
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    await dogrulama_servisi.kanit_bekleyeni_guncelle(oturum, cikti.yetenek_karti_id)
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
    oturum: AsyncSession,
    cikti: SomutCikti,
    arka_plan: BackgroundTasks,
    *,
    yeniden_puanla: bool = False,
) -> None:
    """Kart sürümü artar, commit, sonra kart hazırlama (yeniden eşleştirme) arka planda.

    `yeniden_puanla`: kalemin değerlendirme girdisi değişti (referans desteği);
    kalem önce yeniden puanlanır, sonra kart hazırlanır.
    """
    kart_id, cikti_id = cikti.yetenek_karti_id, cikti.id
    versiyon = await kart_duzenleme.gosterge_degisti(oturum, kart_id)
    await oturum.commit()
    if yeniden_puanla:
        arka_plan.add_task(kart_hazirlama.kalemi_yeniden_puanla, kart_id, cikti_id, versiyon)
    else:
        arka_plan.add_task(kart_hazirlama.karti_hazirla, kart_id, versiyon)


def _eposta_gonder(arka_plan: BackgroundTasks, eposta: Eposta) -> None:
    """Referans e-postası yanıttan sonra gider; hata isteği düşürmez (İ9)."""
    arka_plan.add_task(epostalari_gonder, [eposta])


def referans_gorunumu(referans: ReferansIstegi) -> ReferansIstegiYaniti:
    """Referans isteğini, girişsiz sayfaya açılabilecek alanlara indirger."""
    cikti = referans.somut_cikti
    return ReferansIstegiYaniti(
        somut_cikti_id=cikti.id,
        baslik=cikti.baslik,
        aciklama=cikti.aciklama,
        iddia_sahibi_adi=cikti.yetenek_karti.kullanici.ad,
        pay=cikti.kendi_rolu,
        sonuc=cikti.olculebilir_sonuc,
        durum=referans.durum,
        yanitlanabilir=yanitlanabilir_mi(referans.durum),
    )


async def _sahibinin_referansi(
    oturum: AsyncSession, hesap: Hesap, referans_id: uuid.UUID
) -> tuple[SomutCikti, ReferansIstegi]:
    """Referans isteği ve kalemi; hesap kalemin sahibi değilse 404."""
    referans = await oturum.get(ReferansIstegi, referans_id)
    if referans is None:
        raise bulunamadi(REFERANS_BULUNAMADI)
    cikti = await _sahibinin_ciktisi(oturum, hesap, referans.somut_cikti_id)
    # Kalemle yüklenen listedeki nesne (aynı kimlik haritası) kullanılır.
    return cikti, next(r for r in cikti.referans_istekleri if r.id == referans_id)


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
    if await zaman_asimlarini_isle(oturum, cikti.referans_istekleri):
        await oturum.commit()

    kart = await oturum.get(YetenekKarti, cikti.yetenek_karti_id)
    skor = cikti.guven_skoru
    kararlar = await inceleme.kalem_kararlari(oturum, cikti.id)
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
                iliski=referans.iliski,
                iddia_dogru=referans.iddia_dogru,
                pay_dogru=referans.pay_dogru,
                sonuc_dogru=referans.sonuc_dogru,
                yanit_metni=referans.yanit_metni,
                olusturma_tarihi=referans.olusturma_tarihi,
                guc=eposta_gucu(referans.referans_email),
                guncel=referans_guncel_mi(cikti, referans),
                yeniden_istenebilir=yeniden_isteme_engeli(cikti, referans) is None,
                geri_cekilebilir=referans.durum == DURUM_BEKLIYOR,
            )
            for referans in cikti.referans_istekleri
        ],
        kart_kanit_bekleyen=bool(kart and kart.kanit_bekleyen),
        inceleme_bekliyor=await inceleme.itiraz_bekliyor_mu(oturum, cikti.id),
        dogrulanamadi=bool(kararlar),
        girvak_notlari=[k.girvak_notu for k in kararlar if k.girvak_notu],
    )
