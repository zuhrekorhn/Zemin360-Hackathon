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

from app.agents.eslesme_durumu import (
    OLAY_ILGILENIYORUM,
    OLAY_KABUL,
    OLAY_RED,
    GecersizGecis,
    gecis,
)
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
from app.agents.takip_durumu import ISBIRLIGI_PLAN_BEKLIYOR
from app.api.bildirimler import bildirim_ekle
from app.api.kimlik import rol_gerekli
from app.api.sahiplik import (
    GENCE_ACIK_DURUMLAR,
    bulunamadi,
    girvak_mi,
    ihtiyac_kartinin_sahibi_mi,
    kullanici_id,
    yetenek_kartinin_sahibi_mi,
)
from app.api.sahiplik import kurum_id as hesabin_kurumu
from app.api.yetenek_kartlari import kart_yaniti
from app.core.llm import HizSinirHatasi, ModelMesgulHatasi
from app.db.session import get_session, get_sessionmaker
from app.models.bildirim import TUR_ILGI, TUR_KABUL, TUR_RED, TUR_YENI_ONERI
from app.models.eslesme import Eslesme
from app.models.hesap import ROL_GENC, ROL_GIRVAK, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.isbirligi import Isbirligi
from app.models.kurum import Kurum
from app.models.yetenek_karti import YetenekKarti
from app.schemas.eslestirme import (
    BanaGelenIlgi,
    EslesmeDurumYaniti,
    EslestirmeCalistirIstegi,
    Iletisim,
    IlgileniyorumIstegi,
    KurumOnerisi,
    OnerilerYaniti,
    OneriYaniti,
)

logger = logging.getLogger("zemin360.eslestirme")

router = APIRouter(prefix="/eslestirme", tags=["eslestirme"])

IHTIYAC_YOK = "Kuruma ait ihtiyaç kartı yok"
ESLESME_BULUNAMADI = "Eşleşme bulunamadı"


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
    kurum_id = _hedef_kurum(hesap, istek.kurum_id)
    ihtiyac = await _ihtiyac_karti(oturum, kurum_id, istek.ihtiyac_karti_id)
    return await _pipeline_calistir(oturum, ihtiyac, hesap)


@router.get("/oneriler/{kurum_id}", response_model=OnerilerYaniti)
async def oneriler(
    kurum_id: uuid.UUID,
    ihtiyac_karti_id: uuid.UUID | None = None,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM, ROL_GIRVAK)),
    oturum: AsyncSession = Depends(get_session),
) -> OnerilerYaniti:
    """Hesaplanmış önerileri sıralı döner; hiç hesaplanmamışsa pipeline'ı tetikler.

    `?ihtiyac_karti_id=` verilmezse kurumun en son ihtiyaç kartı (Faz B
    öncesi davranış); kurum panelinde her kart kendi önerilerine gider.
    """
    kurum_id = _hedef_kurum(hesap, kurum_id)
    ihtiyac = await _ihtiyac_karti(oturum, kurum_id, ihtiyac_karti_id)

    mevcut = await _eslesmeleri_oku(oturum, ihtiyac.id)
    if not mevcut:
        return await _pipeline_calistir(oturum, ihtiyac, hesap)

    return await _yanit_kur(oturum, ihtiyac.id, mevcut, hesap)


@router.get("/onerilerim", response_model=list[KurumOnerisi])
async def onerilerim(
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> list[KurumOnerisi]:
    """Kurumun tüm ihtiyaç kartlarındaki öneriler, durumları ve gencin adıyla.

    Yalnızca okur, pipeline çalıştırmaz (dil modeli çağrısı yok): panel her
    açılışta hızlı gelsin. Tazelemek öneriler sayfasının işi. En son hareket
    olan önce.
    """
    eslesmeler = await oturum.scalars(
        _iliskileriyle(select(Eslesme))
        .join(IhtiyacKarti, Eslesme.ihtiyac_karti_id == IhtiyacKarti.id)
        .where(IhtiyacKarti.kurum_id == hesabin_kurumu(hesap))
        .order_by(Eslesme.son_aktivite_tarihi.desc(), Eslesme.skor.desc())
    )
    return [
        KurumOnerisi(
            eslesme_id=eslesme.id,
            durum=eslesme.durum,
            skor=round(eslesme.skor, 4),
            son_aktivite_tarihi=eslesme.son_aktivite_tarihi,
            ihtiyac_karti_id=eslesme.ihtiyac_karti_id,
            problem_tanimi=eslesme.ihtiyac_karti.problem_tanimi,
            yetenek_karti_id=eslesme.yetenek_karti_id,
            genc_adi=eslesme.yetenek_karti.kullanici.ad,
            rol_alani=eslesme.yetenek_karti.rol_alani,
            iletisim=iletisim(eslesme, hesap),
        )
        for eslesme in eslesmeler.all()
    ]


@router.post("/ilgileniyorum", response_model=EslesmeDurumYaniti)
async def ilgileniyorum(
    istek: IlgileniyorumIstegi,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> EslesmeDurumYaniti:
    """Kurum ilgilendiğini söyler: `onerildi` → `ilgileniliyor`.

    İş birliği burada AÇILMAZ; gencin kabulünü bekler
    (docs/faz-b-kimlik-ve-dongu.md § 5). Gence bildirim gider.
    """
    eslesme = await _eslesmeyi_kilitle(oturum, istek.eslesme_id)
    if eslesme is None or not ihtiyac_kartinin_sahibi_mi(hesap, eslesme.ihtiyac_karti):
        raise bulunamadi(ESLESME_BULUNAMADI)
    if _gecisi_uygula(eslesme, OLAY_ILGILENIYORUM, hesap):
        kurum = eslesme.ihtiyac_karti.kurum
        bildirim_ekle(
            oturum,
            eslesme.yetenek_karti.kullanici.hesap_id,
            TUR_ILGI,
            f"{kurum.ad}, “{eslesme.yetenek_karti.rol_alani}” kartınla ilgileniyor. "
            "Kabul edersen e-posta adresleriniz paylaşılır.",
            eslesme.id,
        )
    await oturum.commit()
    return _durum_yaniti(eslesme, hesap)


@router.post("/{eslesme_id}/kabul", response_model=EslesmeDurumYaniti)
async def kabul(
    eslesme_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> EslesmeDurumYaniti:
    """Genç kurumun ilgisini kabul eder: iş birliği açılır, e-postalar görünür."""
    eslesme = await _gencin_eslesmesi(oturum, hesap, eslesme_id)
    if _gecisi_uygula(eslesme, OLAY_KABUL, hesap):
        if eslesme.isbirligi is None:
            eslesme.isbirligi = Isbirligi(
                baslangic_tarihi=dt.date.today(), durum=ISBIRLIGI_PLAN_BEKLIYOR
            )
        bildirim_ekle(
            oturum,
            eslesme.ihtiyac_karti.kurum.hesap_id,
            TUR_KABUL,
            f"{eslesme.yetenek_karti.kullanici.ad} ilgini kabul etti; iletişim bilgileri açıldı.",
            eslesme.id,
        )
    # Durum, iş birliği ve bildirim aynı işlemde: biri yazılıp öbürü kaybolmasın.
    await oturum.commit()
    return _durum_yaniti(eslesme, hesap)


@router.post("/{eslesme_id}/red", response_model=EslesmeDurumYaniti)
async def red(
    eslesme_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> EslesmeDurumYaniti:
    """Genç şu an kabul etmiyor. Kuruma nötr dilde bildirim gider."""
    eslesme = await _gencin_eslesmesi(oturum, hesap, eslesme_id)
    if _gecisi_uygula(eslesme, OLAY_RED, hesap):
        bildirim_ekle(
            oturum,
            eslesme.ihtiyac_karti.kurum.hesap_id,
            TUR_RED,
            f"{eslesme.yetenek_karti.kullanici.ad} bu eşleşmeyi şu an kabul etmedi.",
            eslesme.id,
        )
    await oturum.commit()
    return _durum_yaniti(eslesme, hesap)


@router.get("/bana-gelenler", response_model=list[BanaGelenIlgi])
async def bana_gelenler(
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> list[BanaGelenIlgi]:
    """Gencin kartlarına gelen ilgiler, en yeni hareket önce.

    `onerildi` durumundakiler burada yok: kurum henüz karar vermedi; genç
    eşleşmeyi ancak ilgi bildirildiğinde görür (sahiplik.GENCE_ACIK_DURUMLAR).
    """
    # ihtiyac_kartlari bu modülü içe aktarıyor (arka plan eşleştirmesi); döngü olmasın.
    from app.api.ihtiyac_kartlari import kart_yaniti as ihtiyac_karti_yaniti

    eslesmeler = await oturum.scalars(
        _iliskileriyle(select(Eslesme))
        .join(YetenekKarti, Eslesme.yetenek_karti_id == YetenekKarti.id)
        .where(
            YetenekKarti.kullanici_id == kullanici_id(hesap),
            Eslesme.durum.in_(GENCE_ACIK_DURUMLAR),
        )
        .order_by(Eslesme.son_aktivite_tarihi.desc())
    )
    return [
        BanaGelenIlgi(
            eslesme_id=eslesme.id,
            durum=eslesme.durum,
            son_aktivite_tarihi=eslesme.son_aktivite_tarihi,
            yetenek_karti_id=eslesme.yetenek_karti_id,
            rol_alani=eslesme.yetenek_karti.rol_alani,
            ihtiyac_karti=await ihtiyac_karti_yaniti(oturum, eslesme.ihtiyac_karti_id),
            isbirligi_id=eslesme.isbirligi.id if eslesme.isbirligi else None,
            iletisim=iletisim(eslesme, hesap),
        )
        for eslesme in eslesmeler.all()
    ]


# --- Durum geçişi ----------------------------------------------------------------------


def _iliskileriyle(sorgu):
    """İletişim bilgisi ve sahiplik için gereken ilişkiler: iki taraf ve iş birliği."""
    return sorgu.options(
        selectinload(Eslesme.yetenek_karti).selectinload(YetenekKarti.kullanici),
        selectinload(Eslesme.ihtiyac_karti).selectinload(IhtiyacKarti.kurum),
        selectinload(Eslesme.isbirligi),
    )


async def _eslesmeyi_kilitle(oturum: AsyncSession, eslesme_id: uuid.UUID) -> Eslesme | None:
    """Satırı kilitleyerek okur: çift tıklama iki iş birliği açmasın.

    İkinci istek birincinin commit'ini bekler, sonra güncel durumu okur ve
    geçişi "tekrar" olarak görür.
    """
    return await oturum.scalar(
        _iliskileriyle(select(Eslesme))
        .where(Eslesme.id == eslesme_id)
        .with_for_update(of=Eslesme)
        .execution_options(populate_existing=True)
    )


async def _gencin_eslesmesi(oturum: AsyncSession, hesap: Hesap, eslesme_id: uuid.UUID) -> Eslesme:
    """Gencin kendi kartına ait ve ona açılmış eşleşme; değilse 404.

    `onerildi` durumundaki eşleşme de 404: genç onu henüz göremiyor, varlığı
    sızdırılmaz (sahiplik sözleşmesi).
    """
    eslesme = await _eslesmeyi_kilitle(oturum, eslesme_id)
    if (
        eslesme is None
        or not yetenek_kartinin_sahibi_mi(hesap, eslesme.yetenek_karti)
        or eslesme.durum not in GENCE_ACIK_DURUMLAR
    ):
        raise bulunamadi(ESLESME_BULUNAMADI)
    return eslesme


def _gecisi_uygula(eslesme: Eslesme, olay: str, hesap: Hesap) -> bool:
    """Kuralı `gecis()`'e sorar; değiştiyse durumu ve aktivite tarihini yazar.

    Döner: geçiş gerçekten oldu mu. False = aynı geçişin tekrarı; çağıran yan
    etkiyi (iş birliği, bildirim) tekrarlamaz. Commit çağıranın işi: yan
    etkiler geçişle aynı işlemde yazılsın.
    """
    try:
        sonuc = gecis(eslesme.durum, olay, hesap.rol)
    except GecersizGecis as hata:
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    if sonuc.degisti:
        eslesme.durum = sonuc.durum
        eslesme.son_aktivite_tarihi = dt.datetime.now(dt.UTC)
    return sonuc.degisti


def taraf_mi(hesap: Hesap, eslesme: Eslesme) -> bool:
    """Hesap eşleşmenin iki tarafından biri mi (kartın genci ya da ihtiyacın kurumu)?"""
    return yetenek_kartinin_sahibi_mi(hesap, eslesme.yetenek_karti) or (
        ihtiyac_kartinin_sahibi_mi(hesap, eslesme.ihtiyac_karti)
    )


def iletisim(eslesme: Eslesme, hesap: Hesap | None) -> Iletisim | None:
    """E-postalar yalnızca `kabul_edildi`'de ve yalnızca iki taraftan birine.

    GİRVAK okuma yetkisiyle her şeyi görür ama iletişim bilgisi onun işi
    değil. `eslesme` ilişkileriyle yüklenmiş olmalı (`_iliskileriyle`).
    """
    if eslesme.durum != DURUM_KABUL_EDILDI or hesap is None or not taraf_mi(hesap, eslesme):
        return None
    return Iletisim(
        genc_email=eslesme.yetenek_karti.kullanici.email,
        kurum_email=eslesme.ihtiyac_karti.kurum.iletisim_email,
    )


def _durum_yaniti(eslesme: Eslesme, hesap: Hesap) -> EslesmeDurumYaniti:
    return EslesmeDurumYaniti(
        eslesme_id=eslesme.id,
        durum=eslesme.durum,
        isbirligi_id=eslesme.isbirligi.id if eslesme.isbirligi else None,
        iletisim=iletisim(eslesme, hesap),
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
                await _pipeline_calistir(oturum, ihtiyac)
        except HTTPException as hata:
            logger.info("Arka plan eşleştirme atlandı (%s): %s", ihtiyac_karti_id, hata.detail)
        except Exception:
            logger.exception("Arka plan eşleştirme başarısız (%s)", ihtiyac_karti_id)


# --- Pipeline --------------------------------------------------------------


async def _ihtiyac_karti(
    oturum: AsyncSession, kurum_id: uuid.UUID, ihtiyac_karti_id: uuid.UUID | None
) -> IhtiyacKarti:
    """Kurumun istenen ihtiyaç kartı; verilmezse en sonuncusu. Başka kurumunki 404."""
    if ihtiyac_karti_id is None:
        ihtiyac = await ihtiyac_kartini_getir(oturum, kurum_id)
    else:
        ihtiyac = await oturum.get(IhtiyacKarti, ihtiyac_karti_id)
        if ihtiyac is not None and ihtiyac.kurum_id != kurum_id:
            ihtiyac = None
    if ihtiyac is None:
        raise bulunamadi(IHTIYAC_YOK)
    return ihtiyac


async def _pipeline_calistir(
    oturum: AsyncSession, ihtiyac: IhtiyacKarti, hesap: Hesap | None = None
) -> OnerilerYaniti:
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

    if yeni_oneri:
        bildirim_ekle(
            oturum,
            await oturum.scalar(select(Kurum.hesap_id).where(Kurum.id == ihtiyac.kurum_id)),
            TUR_YENI_ONERI,
            f"İhtiyaç kartın için {yeni_oneri} yeni öneri var.",
        )

    await oturum.commit()

    return await _yanit_kur(oturum, ihtiyac.id, await _eslesmeleri_oku(oturum, ihtiyac.id), hesap)


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
        _iliskileriyle(select(Eslesme))
        .where(Eslesme.ihtiyac_karti_id == ihtiyac_karti_id)
        .order_by(Eslesme.skor.desc())
    )
    return list(satirlar)


async def _yanit_kur(
    oturum: AsyncSession,
    ihtiyac_karti_id: uuid.UUID,
    eslesmeler: list[Eslesme],
    hesap: Hesap | None,
) -> OnerilerYaniti:
    """`hesap` yalnızca iletişim bilgisini kime açacağımızı bilmek için;
    arka plan işi hesapsız çağırır ve yanıtı zaten kimseye dönmez."""
    oneriler = [
        OneriYaniti(
            eslesme_id=eslesme.id,
            skor=round(eslesme.skor, 4),
            durum=eslesme.durum,
            gerekce_metni=eslesme.gerekce_metni,
            yetenek_karti=await kart_yaniti(oturum, eslesme.yetenek_karti_id),
            iletisim=iletisim(eslesme, hesap),
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
