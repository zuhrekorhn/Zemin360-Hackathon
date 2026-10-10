"""GİRVAK özeti ve iş birlikleri listesi (docs/canlilik.md § 7).

Programın altı ihtiyaç alanı için tek bakışlık sayılar ve bütün iş
birliklerinin listesi. Yalnızca GİRVAK; kişisel veri yalnızca ad, e-posta ve
iletişim hiçbir yerde yok. Sayımlar okuma anında hesaplanır, hiçbir şey saklanmaz.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.canlilik_kurallari import ADIM_GECIKTI, YENI_FIRSAT
from app.agents.eslestirme import DURUM_KABUL_EDILDI
from app.agents.inceleme_durumu import ACIK
from app.agents.takip_durumu import ISBIRLIGI_TAMAMLANDI
from app.agents.uygunluk import gorunur_kosulu
from app.api.canlilik import pasif_adaylar
from app.api.kimlik import rol_gerekli
from app.api.takip import ilerleme_hesapla
from app.core.basari_olcutu import hedef_var_mi
from app.db.session import get_session
from app.models.canlilik_olayi import CanlilikOlayi
from app.models.eslesme import Eslesme
from app.models.firma_karti import FirmaKarti
from app.models.guven_skoru import GuvenSkoru
from app.models.hesap import ROL_GENC, ROL_GIRVAK, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.inceleme_isareti import IncelemeIsareti
from app.models.isbirligi import Isbirligi
from app.models.kullanici import Kullanici
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.girvak import (
    AgOzeti,
    DogrulukOzeti,
    EslesmeOzeti,
    GirvakIsbirligi,
    KesifOzeti,
    Ozet,
    TakipOzeti,
    TanimOzeti,
)
from app.servisler.sahiplik import TARAF_ADAY, taraf_adi

router = APIRouter(
    prefix="/girvak", tags=["girvak"], dependencies=[Depends(rol_gerekli(ROL_GIRVAK))]
)

# "Son hatırlatmalar" penceresi (gün).
HATIRLATMA_PENCERESI_GUN = 30
# İş birlikleri listesinin üst sınırı (panel tek sayfa gösterir).
ISBIRLIGI_LISTE_SINIRI = 500


async def _say(oturum: AsyncSession, sorgu) -> int:
    return int(await oturum.scalar(sorgu) or 0)


async def _kesif(oturum: AsyncSession) -> KesifOzeti:
    kayitli = await _say(
        oturum, select(func.count()).select_from(Hesap).where(Hesap.rol == ROL_GENC)
    )
    # Yalnızca hesabı olan profiller (hesapsız profil programın katılımcısı değil).
    kartli = await _say(
        oturum,
        select(func.count(func.distinct(YetenekKarti.kullanici_id)))
        .join(Kullanici, Kullanici.id == YetenekKarti.kullanici_id)
        .where(Kullanici.hesap_id.isnot(None)),
    )
    firsat = await _say(
        oturum,
        select(func.count(func.distinct(Eslesme.yetenek_karti_id))).where(
            Eslesme.yetenek_karti_id.isnot(None), gorunur_kosulu()
        ),
    )
    return KesifOzeti(kayitli_genc=kayitli, kart_olusturan_genc=kartli, firsat_goren_genc=firsat)


async def _dogruluk(oturum: AsyncSession) -> DogrulukOzeti:
    return DogrulukOzeti(
        calisma=await _say(oturum, select(func.count()).select_from(SomutCikti)),
        degerlendirilen_calisma=await _say(
            oturum, select(func.count(func.distinct(GuvenSkoru.somut_cikti_id)))
        ),
        bekleyen_inceleme=await _say(
            oturum,
            select(func.count()).select_from(IncelemeIsareti).where(IncelemeIsareti.durum == ACIK),
        ),
    )


async def _eslesme(oturum: AsyncSession) -> EslesmeOzeti:
    return EslesmeOzeti(
        oneri_toplam=await _say(
            oturum, select(func.count()).select_from(Eslesme).where(gorunur_kosulu())
        ),
        karsilikli_ilgi=await _say(
            oturum,
            select(func.count())
            .select_from(Eslesme)
            .where(Eslesme.durum == DURUM_KABUL_EDILDI, gorunur_kosulu()),
        ),
    )


async def _ag(oturum: AsyncSession, takilanlar: set[tuple]) -> AgOzeti:
    baslangic = dt.datetime.now(dt.UTC) - dt.timedelta(days=HATIRLATMA_PENCERESI_GUN)
    return AgOzeti(
        takilan_surec=len(takilanlar),
        hatirlatma_30_gun=await _say(
            oturum,
            select(func.count())
            .select_from(CanlilikOlayi)
            .where(
                CanlilikOlayi.tetiklenme_tarihi >= baslangic,
                # Yeni fırsat bildirimi hatırlatma değil, gence bir duyuru.
                CanlilikOlayi.tur != YENI_FIRSAT,
            ),
        ),
    )


async def _tanim(oturum: AsyncSession) -> TanimOzeti:
    olcutler = (await oturum.scalars(select(IhtiyacKarti.basari_olcutu))).all()
    return TanimOzeti(
        ihtiyac=len(olcutler),
        # Ölçülebilir = hedef değeri olan ihtiyaç (kural: app/core/basari_olcutu.py).
        olculebilir_ihtiyac=sum(1 for olcut in olcutler if hedef_var_mi(olcut)),
    )


async def _takip(oturum: AsyncSession, takilanlar: set[tuple]) -> TakipOzeti:
    durumlar = await oturum.execute(select(Isbirligi.durum, func.count()).group_by(Isbirligi.durum))
    sayilar = {durum: sayi for durum, sayi in durumlar.all()}
    return TakipOzeti(
        isbirligi=sum(sayilar.values()),
        tamamlanan=sayilar.get(ISBIRLIGI_TAMAMLANDI, 0),
        gecikmis_adim=sum(1 for anahtar in takilanlar if anahtar[1] == ADIM_GECIKTI),
    )


@router.get("/ozet", response_model=Ozet)
async def ozet(oturum: AsyncSession = Depends(get_session)) -> Ozet:
    """Altı ihtiyaç alanı için sayılar (okuma anında; hiçbir şey yazılmaz)."""
    simdi = dt.datetime.now(dt.UTC)
    adaylar = await pasif_adaylar(oturum, simdi, dt.date.today())
    # Takılan süreç = (eşleşme, tür, adım); aynı kaydın iki alıcısı tek sayılır.
    takilanlar = {(e.id, h.tur, h.milestone_id) for e, h, _ in adaylar}
    return Ozet(
        kesif=await _kesif(oturum),
        dogruluk=await _dogruluk(oturum),
        eslesme=await _eslesme(oturum),
        ag=await _ag(oturum, takilanlar),
        tanim=await _tanim(oturum),
        takip=await _takip(oturum, takilanlar),
    )


@router.get("/isbirlikleri", response_model=list[GirvakIsbirligi])
async def isbirlikleri(oturum: AsyncSession = Depends(get_session)) -> list[GirvakIsbirligi]:
    """Bütün iş birlikleri, en son hareket edilen önce. E-posta ve iletişim dönmez."""
    kayitlar = await oturum.scalars(
        select(Isbirligi)
        .join(Eslesme, Isbirligi.eslesme_id == Eslesme.id)
        .options(
            selectinload(Isbirligi.eslesme)
            .selectinload(Eslesme.yetenek_karti)
            .selectinload(YetenekKarti.kullanici),
            selectinload(Isbirligi.eslesme)
            .selectinload(Eslesme.firma_karti)
            .selectinload(FirmaKarti.kurum),
            selectinload(Isbirligi.eslesme)
            .selectinload(Eslesme.ihtiyac_karti)
            .selectinload(IhtiyacKarti.kurum),
            selectinload(Isbirligi.milestonelar),
        )
        .order_by(Eslesme.son_aktivite_tarihi.desc())
        .limit(ISBIRLIGI_LISTE_SINIRI)
    )
    satirlar = []
    for isbirligi in kayitlar.all():
        eslesme = isbirligi.eslesme
        satirlar.append(
            GirvakIsbirligi(
                isbirligi_id=isbirligi.id,
                durum=isbirligi.durum,
                baslangic_tarihi=isbirligi.baslangic_tarihi,
                aday_turu="firma" if eslesme.firma_karti_id else "genc",
                aday_adi=taraf_adi(eslesme, TARAF_ADAY),
                kurum_adi=eslesme.ihtiyac_karti.kurum.ad,
                rol_alani=eslesme.yetenek_karti.rol_alani if eslesme.yetenek_karti else None,
                problem_tanimi=eslesme.ihtiyac_karti.problem_tanimi,
                ilerleme=ilerleme_hesapla(isbirligi.milestonelar),
            )
        )
    return satirlar
