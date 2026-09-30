"""Eşleştirme Ajanı uç noktaları (docs/api-contracts.md § Eşleştirme).

`/eslestirme/calistir` sözleşmede "arka plan işi" olarak geçiyor: Genç ile
Kurum aynı anda platformda olmak zorunda değil. Gerçek bir cron/kuyruk
altyapısı kurmuyoruz (bilinçli, bkz. docs/architecture.md) — bu uç nokta
ileride bir zamanlayıcının çağıracağı "asıl işi yapan" kanca; şimdilik
doğrudan da çağrılabiliyor.

Pipeline'ın kendisi app/servisler/eslestirme.py'de (ihtiyaç onayının arka
plan işi de onu çağırıyor); bu modül yetki, durum geçişi ve yanıt şeması.
"""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.eslesme_durumu import (
    OLAY_GENC_ILGI,
    OLAY_ILGILENIYORUM,
    OLAY_ILGIYI_GERI_CEK,
    OLAY_KABUL,
    OLAY_RED,
    OLAY_SIMDILIK_DEGIL,
    GecersizGecis,
    gecis,
    ilgi_engeli,
)
from app.agents.eslestirme import (
    DURUM_GENC_ILGILENDI,
    DURUM_ONERILDI,
    SKOR_ESIGI,
    TOP_N,
    firma_tamamlanan_isbirligi_sayilari,
    ihtiyac_kartini_getir,
)
from app.api import takip
from app.api.bildirimler import bildirim_ekle
from app.api.ihtiyac_kartlari import kart_yaniti as ihtiyac_karti_yaniti
from app.api.kimlik import rol_gerekli
from app.api.sahiplik import (
    GENCE_ACIK_DURUMLAR,
    TARAF_ADAY,
    TARAF_ILAN,
    bulunamadi,
    eslesmedeki_taraf,
    girvak_mi,
    kullanici_id,
    taraf_adi,
    taraf_hesabi,
)
from app.api.sahiplik import kurum_id as hesabin_kurumu
from app.api.yetenek_kartlari import kart_yaniti
from app.core.firma_dogrulama import DOGRULANDI
from app.db.session import get_session
from app.models.bildirim import (
    TUR_FIRSAT_KAPANDI,
    TUR_GENC_ILGI,
    TUR_ILGI,
    TUR_KABUL,
    TUR_KARSILIKLI_ILGI,
    TUR_RED,
)
from app.models.eslesme import Eslesme
from app.models.firma_karti import FirmaKarti
from app.models.hesap import ROL_GENC, ROL_GIRVAK, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.eslestirme import (
    BanaGelenIlgi,
    EslesmeDurumYaniti,
    EslestirmeCalistirIstegi,
    FirmaAdayEslesmesi,
    FirmaAdayKarti,
    GencEslesmesi,
    GencIlgiIstegi,
    IlgileniyorumIstegi,
    KurumOnerisi,
    OnerilerYaniti,
    OneriYaniti,
)
from app.servisler import eslestirme as servis
from app.servisler.eslestirme import (
    IHTIYAC_ACIK,
    eslesmeleri_oku,
    iletisim,
    iliskileriyle,
)
from app.servisler.ilgi import firsat_kapandi_metni, isbirligini_ac

router = APIRouter(prefix="/eslestirme", tags=["eslestirme"])

IHTIYAC_YOK = "Kuruma ait ihtiyaç kartı yok"
# Faz B'de yalnızca kurum ilgi gösterebiliyordu: bu durumlardaki eski kayıtlar
# kurumun ilgisiyle başladı.
KURUM_ILGISI_DURUMLARI = ("ilgileniliyor", "kabul_edildi", "reddedildi")
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

    mevcut = await eslesmeleri_oku(oturum, ihtiyac.id)
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
        iliskileriyle(select(Eslesme))
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
            aday_turu="firma" if eslesme.firma_karti_id else "genc",
            aday_adi=taraf_adi(eslesme, TARAF_ADAY),
            yetenek_karti_id=eslesme.yetenek_karti_id,
            firma_karti_id=eslesme.firma_karti_id,
            genc_adi=eslesme.yetenek_karti.kullanici.ad if eslesme.yetenek_karti else None,
            rol_alani=eslesme.yetenek_karti.rol_alani if eslesme.yetenek_karti else None,
            iletisim=iletisim(eslesme, hesap),
        )
        for eslesme in eslesmeler.all()
    ]


@router.post("/ilgileniyorum", response_model=EslesmeDurumYaniti)
async def ilgileniyorum(
    istek: IlgileniyorumIstegi,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> EslesmeDurumYaniti:
    """Kurum ilgilendiğini söyler. İki kapı:

    - `onerildi` → `ilgileniliyor`: iş birliği AÇILMAZ, gencin kabulünü bekler
      (docs/faz-b-kimlik-ve-dongu.md § 5). Gence bildirim gider.
    - `genc_ilgilendi` → `kabul_edildi` (karşılıklı ilgi): genç onayını ilgi
      gösterirken verdi; iş birliği açılır, e-postalar iki tarafa görünür,
      yanıttan sonra plan önerilir (docs/plans/genc-akisi.md § 4).
    """
    eslesme = await _ilan_tarafinin_eslesmesi(oturum, hesap, istek.eslesme_id)
    karsilikli = eslesme.durum == DURUM_GENC_ILGILENDI
    degisti = _gecisi_uygula(eslesme, OLAY_ILGILENIYORUM, TARAF_ILAN)
    if degisti:
        eslesme.kurum_ilgi_tarihi = eslesme.son_aktivite_tarihi
        if karsilikli:
            isbirligini_ac(eslesme)
            bildirim_ekle(
                oturum,
                taraf_hesabi(eslesme, TARAF_ADAY),
                TUR_KARSILIKLI_ILGI,
                # Adın ardında ek yok: "de/da" ünlü uyumu ada göre değişir.
                # Aday firmaya "siz", gence "sen" (docs/icerik-rehberi.md).
                f"{taraf_adi(eslesme, TARAF_ILAN)} "
                + ("ilginize" if eslesme.firma_karti_id else "ilgine")
                + " karşılık verdi. İletişim bilgileriniz paylaşıldı ve iş birliği başladı.",
                eslesme.id,
            )
        else:
            eslesme.baslatan = TARAF_ILAN
            bildirim_ekle(
                oturum,
                taraf_hesabi(eslesme, TARAF_ADAY),
                TUR_ILGI,
                _ilgi_bildirimi(eslesme),
                eslesme.id,
            )
    await oturum.commit()
    if degisti and karsilikli and eslesme.isbirligi is not None:
        arka_plan.add_task(takip.plani_arka_planda_oner, eslesme.isbirligi.id)
    return _durum_yaniti(eslesme, hesap)


@router.post("/{eslesme_id}/genc-ilgi", response_model=EslesmeDurumYaniti)
async def genc_ilgi(
    eslesme_id: uuid.UUID,
    istek: GencIlgiIstegi,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> EslesmeDurumYaniti:
    """Genç bir fırsata ilgi gösterir: `onerildi` → `genc_ilgilendi`.

    Yalnızca eşik üstü ve açık ihtiyaç (409, nedeniyle). İlgi skoru değiştirmez;
    firma ekranında ayrı bir işaret. `iletisim_onayi` zorunlu: firma da
    ilgilenirse e-posta firmayla paylaşılır. Firmaya bildirim gider.
    """
    eslesme = await _gencin_eslesmesi(oturum, hesap, eslesme_id)
    if eslesme.durum == DURUM_ONERILDI:
        engel = ilgi_engeli(eslesme.skor, eslesme.ihtiyac_karti.durum)
        if engel:
            raise HTTPException(status_code=409, detail=engel)
    if _gecisi_uygula(eslesme, OLAY_GENC_ILGI, TARAF_ADAY):
        eslesme.baslatan = TARAF_ADAY
        eslesme.genc_ilgi_tarihi = eslesme.son_aktivite_tarihi
        eslesme.genc_iletisim_onayi_tarihi = eslesme.son_aktivite_tarihi
        bildirim_ekle(
            oturum,
            taraf_hesabi(eslesme, TARAF_ILAN),
            TUR_GENC_ILGI,
            f"{taraf_adi(eslesme, TARAF_ADAY)} ihtiyacınızla ilgileniyor. Siz de "
            "ilgilenirseniz iletişim bilgileriniz karşılıklı paylaşılır.",
            eslesme.id,
        )
    await oturum.commit()
    return _durum_yaniti(eslesme, hesap)


@router.post("/{eslesme_id}/ilgiyi-geri-cek", response_model=EslesmeDurumYaniti)
async def ilgiyi_geri_cek(
    eslesme_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> EslesmeDurumYaniti:
    """Genç ilgisini, karşılıklı hâle gelmeden geri çeker: `genc_ilgilendi` → `onerildi`.

    İlgi kaydı ve iletişim onayı silinir. Karşılıklı ilgiden sonra 409.
    Firmaya bildirim gitmez: firmanın ekranındaki işaret kalkar.
    """
    eslesme = await _gencin_eslesmesi(oturum, hesap, eslesme_id)
    if _gecisi_uygula(eslesme, OLAY_ILGIYI_GERI_CEK, TARAF_ADAY):
        eslesme.baslatan = None
        eslesme.genc_ilgi_tarihi = None
        eslesme.genc_iletisim_onayi_tarihi = None
    await oturum.commit()
    return _durum_yaniti(eslesme, hesap)


@router.post("/{eslesme_id}/simdilik-degil", response_model=EslesmeDurumYaniti)
async def simdilik_degil(
    eslesme_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> EslesmeDurumYaniti:
    """Firma, ilgi gösteren gence "şimdilik değil" der: `genc_ilgilendi` → `kapandi`.

    Gence nötr bildirim ("fırsat kapandı"; ret ifadesi ve neden yok).
    """
    eslesme = await _ilan_tarafinin_eslesmesi(oturum, hesap, eslesme_id)
    if _gecisi_uygula(eslesme, OLAY_SIMDILIK_DEGIL, TARAF_ILAN):
        bildirim_ekle(
            oturum,
            taraf_hesabi(eslesme, TARAF_ADAY),
            TUR_FIRSAT_KAPANDI,
            firsat_kapandi_metni(taraf_adi(eslesme, TARAF_ILAN)),
            eslesme.id,
        )
    await oturum.commit()
    return _durum_yaniti(eslesme, hesap)


@router.post("/{eslesme_id}/kabul", response_model=EslesmeDurumYaniti)
async def kabul(
    eslesme_id: uuid.UUID,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> EslesmeDurumYaniti:
    """Genç kurumun ilgisini kabul eder: iş birliği açılır, e-postalar görünür.

    Yanıttan sonra Takip Ajanı planı önerir (docs/faz-c-takip.md § 4).
    """
    eslesme = await _gencin_eslesmesi(oturum, hesap, eslesme_id)
    degisti = _gecisi_uygula(eslesme, OLAY_KABUL, TARAF_ADAY)
    if degisti:
        isbirligini_ac(eslesme)
        bildirim_ekle(
            oturum,
            taraf_hesabi(eslesme, TARAF_ILAN),
            TUR_KABUL,
            f"{taraf_adi(eslesme, TARAF_ADAY)} ilgini kabul etti; iletişim bilgileri açıldı.",
            eslesme.id,
        )
    # Durum, iş birliği ve bildirim aynı işlemde: biri yazılıp öbürü kaybolmasın.
    await oturum.commit()
    if degisti and eslesme.isbirligi is not None:
        arka_plan.add_task(takip.plani_arka_planda_oner, eslesme.isbirligi.id)
    return _durum_yaniti(eslesme, hesap)


@router.post("/{eslesme_id}/red", response_model=EslesmeDurumYaniti)
async def red(
    eslesme_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> EslesmeDurumYaniti:
    """Genç şu an kabul etmiyor. Kuruma nötr dilde bildirim gider."""
    eslesme = await _gencin_eslesmesi(oturum, hesap, eslesme_id)
    if _gecisi_uygula(eslesme, OLAY_RED, TARAF_ADAY):
        bildirim_ekle(
            oturum,
            taraf_hesabi(eslesme, TARAF_ILAN),
            TUR_RED,
            f"{taraf_adi(eslesme, TARAF_ADAY)} bu eşleşmeyi şu an kabul etmedi.",
            eslesme.id,
        )
    await oturum.commit()
    return _durum_yaniti(eslesme, hesap)


@router.get("/bana-gelenler", response_model=list[BanaGelenIlgi])
async def bana_gelenler(
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> list[BanaGelenIlgi]:
    """Gencin kartlarına kurumun gösterdiği ilgiler, en yeni hareket önce.

    Yalnızca ilk ilgiyi kurumun gösterdiği kayıtlar (`baslatan = kurum`; eski
    kayıtlar migration'la öyle işaretlendi). Gencin kendi gösterdiği ilgiler
    ve henüz ilgisiz öneriler gencin fırsat listesinde (genç ana sayfası).
    """
    eslesmeler = await oturum.scalars(
        iliskileriyle(select(Eslesme))
        .join(YetenekKarti, Eslesme.yetenek_karti_id == YetenekKarti.id)
        .where(
            YetenekKarti.kullanici_id == kullanici_id(hesap),
            or_(
                Eslesme.baslatan == TARAF_ILAN,
                # Başlatanı bilinmeyen (alan eklenmeden yazılmış) kurum ilgisi.
                and_(Eslesme.baslatan.is_(None), Eslesme.durum.in_(KURUM_ILGISI_DURUMLARI)),
            ),
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


async def _gencin_satirlari(oturum: AsyncSession, hesap: Hesap, *kosullar) -> list[GencEslesmesi]:
    eslesmeler = await oturum.scalars(
        iliskileriyle(select(Eslesme))
        .join(YetenekKarti, Eslesme.yetenek_karti_id == YetenekKarti.id)
        .join(IhtiyacKarti, Eslesme.ihtiyac_karti_id == IhtiyacKarti.id)
        .where(YetenekKarti.kullanici_id == kullanici_id(hesap), *kosullar)
        .order_by(Eslesme.skor.desc(), Eslesme.son_aktivite_tarihi.desc())
    )
    return [
        GencEslesmesi(
            eslesme_id=eslesme.id,
            durum=eslesme.durum,
            uyum=round(eslesme.skor, 4),
            gerekce_metni=eslesme.gerekce_metni,
            son_aktivite_tarihi=eslesme.son_aktivite_tarihi,
            yetenek_karti_id=eslesme.yetenek_karti_id,
            rol_alani=eslesme.yetenek_karti.rol_alani,
            ihtiyac_karti=await ihtiyac_karti_yaniti(oturum, eslesme.ihtiyac_karti_id),
            isbirligi_id=eslesme.isbirligi.id if eslesme.isbirligi else None,
            iletisim=iletisim(eslesme, hesap),
        )
        for eslesme in eslesmeler.all()
    ]


@router.get("/firsatlarim", response_model=list[GencEslesmesi])
async def firsatlarim(
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> list[GencEslesmesi]:
    """Sana uygun fırsatlar: gencin kartlarının eşik üstü, açık ihtiyaçlardaki
    henüz ilgi gösterilmemiş önerileri, uyum sırasıyla (plan § 7).

    Yalnızca okur, eşleştirme çalıştırmaz. Açık bir ilan panosu değil: genç
    yalnızca kendi kartına önerilmiş ihtiyaçları görür.
    """
    return await _gencin_satirlari(
        oturum,
        hesap,
        Eslesme.durum == DURUM_ONERILDI,
        Eslesme.skor >= SKOR_ESIGI,
        IhtiyacKarti.durum == IHTIYAC_ACIK,
    )


@router.get("/ilgilerim", response_model=list[GencEslesmesi])
async def ilgilerim(
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> list[GencEslesmesi]:
    """Gencin kendi gösterdiği ilgiler ve durumları: beklemede, karşılıklı ilgi, kapandı.

    Firmanın başlattığı ilgiler "bana gelenler"de.
    """
    return await _gencin_satirlari(oturum, hesap, Eslesme.baslatan == TARAF_ADAY)


# --- Durum geçişi ----------------------------------------------------------------------


async def _eslesmeyi_kilitle(oturum: AsyncSession, eslesme_id: uuid.UUID) -> Eslesme | None:
    """Satırı kilitleyerek okur: çift tıklama iki iş birliği açmasın.

    İkinci istek birincinin commit'ini bekler, sonra güncel durumu okur ve
    geçişi "tekrar" olarak görür.
    """
    return await oturum.scalar(
        iliskileriyle(select(Eslesme))
        .where(Eslesme.id == eslesme_id)
        .with_for_update(of=Eslesme)
        .execution_options(populate_existing=True)
    )


async def _gencin_eslesmesi(oturum: AsyncSession, hesap: Hesap, eslesme_id: uuid.UUID) -> Eslesme:
    """Gencin kendi kartına ait eşleşme; değilse 404 (varlık sızdırılmaz).

    Genç akışında (plan § 0, karar 1) genç kendi kartının bütün eşleşmelerini
    görür (sahiplik.GENCE_ACIK_DURUMLAR).
    """
    eslesme = await _eslesmeyi_kilitle(oturum, eslesme_id)
    if (
        eslesme is None
        or eslesmedeki_taraf(hesap, eslesme) != TARAF_ADAY
        or eslesme.durum not in GENCE_ACIK_DURUMLAR
    ):
        raise bulunamadi(ESLESME_BULUNAMADI)
    return eslesme


async def _ilan_tarafinin_eslesmesi(
    oturum: AsyncSession, hesap: Hesap, eslesme_id: uuid.UUID
) -> Eslesme:
    """İlanın sahibi firmanın eşleşmesi (kilitli); değilse 404."""
    eslesme = await _eslesmeyi_kilitle(oturum, eslesme_id)
    if eslesme is None or eslesmedeki_taraf(hesap, eslesme) != TARAF_ILAN:
        raise bulunamadi(ESLESME_BULUNAMADI)
    return eslesme


def _gecisi_uygula(eslesme: Eslesme, olay: str, taraf: str) -> bool:
    """Kuralı `gecis()`'e sorar; değiştiyse durumu ve aktivite tarihini yazar.

    `taraf`: eşleşmedeki taraf (aday / ilan), hesabın rolü değil
    (docs/plans/firma-akisi.md § 3). Çağıran tarafı sahiplikle doğrulamış olmalı.

    Döner: geçiş gerçekten oldu mu. False = aynı geçişin tekrarı; çağıran yan
    etkiyi (iş birliği, bildirim) tekrarlamaz. Commit çağıranın işi: yan
    etkiler geçişle aynı işlemde yazılsın.
    """
    try:
        sonuc = gecis(eslesme.durum, olay, taraf, baslatan=eslesme.baslatan)
    except GecersizGecis as hata:
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    if sonuc.degisti:
        eslesme.durum = sonuc.durum
        eslesme.son_aktivite_tarihi = dt.datetime.now(dt.UTC)
    return sonuc.degisti


def _durum_yaniti(eslesme: Eslesme, hesap: Hesap) -> EslesmeDurumYaniti:
    return EslesmeDurumYaniti(
        eslesme_id=eslesme.id,
        durum=eslesme.durum,
        isbirligi_id=eslesme.isbirligi.id if eslesme.isbirligi else None,
        iletisim=iletisim(eslesme, hesap),
    )


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
    """Pipeline'ı çalıştırır (app/servisler/eslestirme.py) ve yanıtı kurar."""
    eslesmeler = await servis.pipeline_calistir(oturum, ihtiyac)
    return await _yanit_kur(oturum, ihtiyac.id, eslesmeler, hesap)


async def _yanit_kur(
    oturum: AsyncSession,
    ihtiyac_karti_id: uuid.UUID,
    eslesmeler: list[Eslesme],
    hesap: Hesap | None,
) -> OnerilerYaniti:
    """`hesap` yalnızca iletişim bilgisini kime açacağımızı bilmek için;
    arka plan işi hesapsız çağırır ve yanıtı zaten kimseye dönmez.

    Aday genç ise yetenek kartı, firma ise firma kartı döner (tam biri).
    """
    isbirlikleri = await firma_tamamlanan_isbirligi_sayilari(
        oturum, [e.firma_karti_id for e in eslesmeler if e.firma_karti_id]
    )
    oneriler = [
        OneriYaniti(
            eslesme_id=eslesme.id,
            skor=round(eslesme.skor, 4),
            durum=eslesme.durum,
            gerekce_metni=eslesme.gerekce_metni,
            aday_turu="firma" if eslesme.firma_karti_id else "genc",
            yetenek_karti=(
                await kart_yaniti(oturum, eslesme.yetenek_karti_id)
                if eslesme.yetenek_karti_id
                else None
            ),
            firma_karti=(
                _firma_aday_karti(eslesme, isbirlikleri.get(eslesme.firma_karti_id, 0))
                if eslesme.firma_karti_id
                else None
            ),
            iletisim=iletisim(eslesme, hesap),
            genc_ilgi_gosterdi=eslesme.durum == DURUM_GENC_ILGILENDI,
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


def _firma_aday_karti(eslesme: Eslesme, tamamlanan_isbirligi: int) -> FirmaAdayKarti:
    """`eslesme` ilişkileriyle yüklenmiş olmalı (`iliskileriyle`)."""
    kart = eslesme.firma_karti
    kurum = kart.kurum
    return FirmaAdayKarti(
        firma_karti_id=kart.id,
        kurum_id=kurum.id,
        firma_adi=kurum.ad,
        tur=kurum.tur,
        sektor=kurum.sektor,
        sehir=kurum.sehir,
        dogrulandi=kurum.dogrulama_durumu == DOGRULANDI,
        ne_yapiyoruz=kart.ne_yapiyoruz,
        yetkinlikler=list(kart.yetkinlikler),
        onceki_isler=kart.onceki_isler,
        isbirligi_turleri=list(kart.isbirligi_turleri),
        tamamlanan_isbirligi=tamamlanan_isbirligi,
    )


# --- Firmalar arası ilgi: aday firmanın tarafı (docs/plans/firma-akisi.md § 0 karar 8, § 3) ---
#
# Durum makinesi aynı; aday firma makinenin "aday tarafı"nın geçişlerini yapar
# (genç uçlarının aynısı). Uçlar ayrı ve ince: rol firma, taraf aday. Metinler
# firmaya "siz" (docs/icerik-rehberi.md).


def _ilgi_bildirimi(eslesme: Eslesme) -> str:
    """İlan tarafı ilk ilgiyi gösterdiğinde adaya giden bildirim."""
    ilan_firmasi = taraf_adi(eslesme, TARAF_ILAN)
    if eslesme.firma_karti_id:
        return (
            f"{ilan_firmasi}, iş birliği ilanı için firmanızla ilgileniyor. "
            "Kabul ederseniz e-posta adresleriniz paylaşılır."
        )
    return (
        f"{ilan_firmasi}, “{eslesme.yetenek_karti.rol_alani}” kartınla ilgileniyor. "
        "Kabul edersen e-posta adresleriniz paylaşılır."
    )


async def _aday_firmanin_eslesmesi(
    oturum: AsyncSession, hesap: Hesap, eslesme_id: uuid.UUID
) -> Eslesme:
    """Aday firmanın eşleşmesi (kilitli); firma adayı değilse ya da taraf değilse 404."""
    eslesme = await _eslesmeyi_kilitle(oturum, eslesme_id)
    if (
        eslesme is None
        or eslesme.firma_karti_id is None
        or eslesmedeki_taraf(hesap, eslesme) != TARAF_ADAY
    ):
        raise bulunamadi(ESLESME_BULUNAMADI)
    return eslesme


@router.post("/{eslesme_id}/firma-ilgi", response_model=EslesmeDurumYaniti)
async def firma_ilgi(
    eslesme_id: uuid.UUID,
    istek: GencIlgiIstegi,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> EslesmeDurumYaniti:
    """Aday firma bir ortak ilanına ilgi gösterir: `onerildi` → `genc_ilgilendi`.

    Gençtekiyle aynı kural: yalnızca eşik üstü ve açık ilan; `iletisim_onayi`
    zorunlu (ilan sahibi de ilgilenirse e-posta paylaşılır).
    """
    eslesme = await _aday_firmanin_eslesmesi(oturum, hesap, eslesme_id)
    if eslesme.durum == DURUM_ONERILDI:
        engel = ilgi_engeli(eslesme.skor, eslesme.ihtiyac_karti.durum)
        if engel:
            raise HTTPException(status_code=409, detail=engel)
    if _gecisi_uygula(eslesme, OLAY_GENC_ILGI, TARAF_ADAY):
        eslesme.baslatan = TARAF_ADAY
        eslesme.genc_ilgi_tarihi = eslesme.son_aktivite_tarihi
        eslesme.genc_iletisim_onayi_tarihi = eslesme.son_aktivite_tarihi
        bildirim_ekle(
            oturum,
            taraf_hesabi(eslesme, TARAF_ILAN),
            TUR_GENC_ILGI,
            f"{taraf_adi(eslesme, TARAF_ADAY)} iş birliği ilanınızla ilgileniyor. Siz de "
            "ilgilenirseniz iletişim bilgileriniz karşılıklı paylaşılır.",
            eslesme.id,
        )
    await oturum.commit()
    return _durum_yaniti(eslesme, hesap)


@router.post("/{eslesme_id}/firma-ilgiyi-geri-cek", response_model=EslesmeDurumYaniti)
async def firma_ilgiyi_geri_cek(
    eslesme_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> EslesmeDurumYaniti:
    """Karşılıklı olmadan geri çekme: `genc_ilgilendi` → `onerildi`; bildirim yok."""
    eslesme = await _aday_firmanin_eslesmesi(oturum, hesap, eslesme_id)
    if _gecisi_uygula(eslesme, OLAY_ILGIYI_GERI_CEK, TARAF_ADAY):
        eslesme.baslatan = None
        eslesme.genc_ilgi_tarihi = None
        eslesme.genc_iletisim_onayi_tarihi = None
    await oturum.commit()
    return _durum_yaniti(eslesme, hesap)


@router.post("/{eslesme_id}/firma-kabul", response_model=EslesmeDurumYaniti)
async def firma_kabul(
    eslesme_id: uuid.UUID,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> EslesmeDurumYaniti:
    """Aday firma ilan sahibinin ilgisini kabul eder: iş birliği açılır, e-postalar görünür."""
    eslesme = await _aday_firmanin_eslesmesi(oturum, hesap, eslesme_id)
    degisti = _gecisi_uygula(eslesme, OLAY_KABUL, TARAF_ADAY)
    if degisti:
        isbirligini_ac(eslesme)
        bildirim_ekle(
            oturum,
            taraf_hesabi(eslesme, TARAF_ILAN),
            TUR_KABUL,
            f"{taraf_adi(eslesme, TARAF_ADAY)} ilginizi kabul etti; iletişim bilgileri açıldı.",
            eslesme.id,
        )
    await oturum.commit()
    if degisti and eslesme.isbirligi is not None:
        arka_plan.add_task(takip.plani_arka_planda_oner, eslesme.isbirligi.id)
    return _durum_yaniti(eslesme, hesap)


@router.post("/{eslesme_id}/firma-red", response_model=EslesmeDurumYaniti)
async def firma_red(
    eslesme_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> EslesmeDurumYaniti:
    """Aday firma şu an kabul etmiyor; ilan sahibine nötr bildirim."""
    eslesme = await _aday_firmanin_eslesmesi(oturum, hesap, eslesme_id)
    if _gecisi_uygula(eslesme, OLAY_RED, TARAF_ADAY):
        bildirim_ekle(
            oturum,
            taraf_hesabi(eslesme, TARAF_ILAN),
            TUR_RED,
            f"{taraf_adi(eslesme, TARAF_ADAY)} bu eşleşmeyi şu an kabul etmedi.",
            eslesme.id,
        )
    await oturum.commit()
    return _durum_yaniti(eslesme, hesap)


@router.get("/firma-eslesmelerim", response_model=list[FirmaAdayEslesmesi])
async def firma_eslesmelerim(
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> list[FirmaAdayEslesmesi]:
    """Firmanın aday olduğu bütün eşleşmeler, uyum sırasıyla (yalnızca okur).

    Fırsatlar (önerilmiş; eşik altı ve kapalı ilan burada süzülür), gelen
    ilgiler ve kendi ilgileri arayüzde ayrılır (`lib/firma-ilgi.ts`). Açık ilan panosu değil:
    firma yalnızca kendi kartına önerilmiş ilanları görür.
    """
    eslesmeler = await oturum.scalars(
        iliskileriyle(select(Eslesme))
        .join(FirmaKarti, Eslesme.firma_karti_id == FirmaKarti.id)
        .join(IhtiyacKarti, Eslesme.ihtiyac_karti_id == IhtiyacKarti.id)
        .where(
            FirmaKarti.kurum_id == hesabin_kurumu(hesap),
            # Fırsat yalnızca eşik üstü ve açık ilanda (gencin fırsatlarındaki kural);
            # ilgi gösterilmiş ya da karar verilmiş kayıtlar her durumda listede.
            or_(
                Eslesme.durum != DURUM_ONERILDI,
                and_(Eslesme.skor >= SKOR_ESIGI, IhtiyacKarti.durum == IHTIYAC_ACIK),
            ),
        )
        .order_by(Eslesme.skor.desc(), Eslesme.son_aktivite_tarihi.desc())
    )
    return [
        FirmaAdayEslesmesi(
            eslesme_id=eslesme.id,
            durum=eslesme.durum,
            uyum=round(eslesme.skor, 4),
            gerekce_metni=eslesme.gerekce_metni,
            son_aktivite_tarihi=eslesme.son_aktivite_tarihi,
            baslatan=eslesme.baslatan,
            ihtiyac_karti=await ihtiyac_karti_yaniti(oturum, eslesme.ihtiyac_karti_id),
            isbirligi_id=eslesme.isbirligi.id if eslesme.isbirligi else None,
            iletisim=iletisim(eslesme, hesap),
        )
        for eslesme in eslesmeler.all()
    ]
