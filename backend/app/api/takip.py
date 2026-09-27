"""Takip Ajanı uç noktaları (docs/faz-c-takip.md § 7).

İş birliği sayfası iki tarafa aynı görünümdür; GİRVAK yalnızca okur ve
e-postaları görmez. Kurallar iki saf fonksiyonda (app/agents/takip_durumu.py),
bu modül yalnızca uygular: yetki, veritabanı, bildirim.

Sahiplik (Faz B sözleşmesi): 401 token yok, 403 rol uygun değil (GİRVAK
yazamaz), 404 başkasının iş birliği.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents import takip
from app.agents.takip_durumu import (
    ISBIRLIGI_PLAN_BEKLIYOR,
    MILESTONE_BEKLIYOR,
    MILESTONE_TAMAMLANDI,
    PLAN_DUZENLE,
    GecersizTakipGecisi,
    PlanDurumu,
    PlanSonucu,
    RolUygunDegil,
    gecikmis_mi,
    plan_gecisi,
)
from app.api.bildirimler import bildirim_ekle
from app.api.kimlik import rol_gerekli
from app.api.sahiplik import (
    bulunamadi,
    girvak_mi,
    ihtiyac_kartinin_sahibi_mi,
    yetenek_kartinin_sahibi_mi,
)
from app.db.session import get_session, get_sessionmaker
from app.models.bildirim import TUR_PLAN_DUZENLENDI, TUR_PLAN_ONERILDI
from app.models.eslesme import Eslesme
from app.models.hesap import ROL_GENC, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.isbirligi import Isbirligi
from app.models.milestone import Milestone
from app.models.yetenek_karti import YetenekKarti
from app.schemas.takip import Ilerleme, IsbirligiDetayi, MilestoneYaniti

logger = logging.getLogger("zemin360.takip")

router = APIRouter(prefix="/isbirligi", tags=["takip"])

ISBIRLIGI_BULUNAMADI = "İş birliği bulunamadı"
PLAN_ONERILEMEDI = (
    "Plan şu an önerilemedi. Adımları elle ekleyebilir ya da biraz sonra yeniden deneyebilirsin."
)


# --- Okuma ve yetki ---------------------------------------------------------------------


def _iliskileriyle(sorgu):
    """Görünüm, sahiplik ve plan istemi için gereken her şey tek seferde."""
    eslesme = selectinload(Isbirligi.eslesme)
    return sorgu.options(
        eslesme.selectinload(Eslesme.yetenek_karti).selectinload(YetenekKarti.kullanici),
        eslesme.selectinload(Eslesme.yetenek_karti).selectinload(YetenekKarti.somut_ciktilar),
        eslesme.selectinload(Eslesme.ihtiyac_karti).selectinload(IhtiyacKarti.kurum),
        selectinload(Isbirligi.milestonelar),
    )


async def isbirligini_getir(
    oturum: AsyncSession, isbirligi_id: uuid.UUID, *, kilitle: bool = False
) -> Isbirligi | None:
    """`kilitle`: yazan istekler satırı kilitler; çift tıklama iki kez uygulanmasın."""
    sorgu = (
        _iliskileriyle(select(Isbirligi))
        .where(Isbirligi.id == isbirligi_id)
        .execution_options(populate_existing=True)
    )
    if kilitle:
        sorgu = sorgu.with_for_update(of=Isbirligi)
    return await oturum.scalar(sorgu)


def taraf_rolu(hesap: Hesap, isbirligi: Isbirligi) -> str | None:
    """Hesap bu iş birliğinin genci mi, kurumu mu? Değilse None."""
    eslesme = isbirligi.eslesme
    if yetenek_kartinin_sahibi_mi(hesap, eslesme.yetenek_karti):
        return ROL_GENC
    if ihtiyac_kartinin_sahibi_mi(hesap, eslesme.ihtiyac_karti):
        return ROL_KURUM
    return None


async def okunabilir_isbirligi(
    oturum: AsyncSession, hesap: Hesap, isbirligi_id: uuid.UUID
) -> Isbirligi:
    isbirligi = await isbirligini_getir(oturum, isbirligi_id)
    if isbirligi is None or not (girvak_mi(hesap) or taraf_rolu(hesap, isbirligi)):
        raise bulunamadi(ISBIRLIGI_BULUNAMADI)
    return isbirligi


async def yazilabilir_isbirligi(
    oturum: AsyncSession, hesap: Hesap, isbirligi_id: uuid.UUID
) -> tuple[Isbirligi, str]:
    """Kilitli okur; yalnızca iki taraf. Döner: (iş birliği, çağıranın rolü)."""
    isbirligi = await isbirligini_getir(oturum, isbirligi_id, kilitle=True)
    rol = taraf_rolu(hesap, isbirligi) if isbirligi is not None else None
    if isbirligi is None or rol is None:
        raise bulunamadi(ISBIRLIGI_BULUNAMADI)
    return isbirligi, rol


# --- Yardımcılar ------------------------------------------------------------------------


def _simdi() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def taraf_adi(isbirligi: Isbirligi, rol: str) -> str:
    eslesme = isbirligi.eslesme
    return eslesme.yetenek_karti.kullanici.ad if rol == ROL_GENC else eslesme.ihtiyac_karti.kurum.ad


def taraf_hesabi(isbirligi: Isbirligi, rol: str) -> uuid.UUID | None:
    eslesme = isbirligi.eslesme
    if rol == ROL_GENC:
        return eslesme.yetenek_karti.kullanici.hesap_id
    return eslesme.ihtiyac_karti.kurum.hesap_id


def karsi_rol(rol: str) -> str:
    return ROL_KURUM if rol == ROL_GENC else ROL_GENC


def aktivite(isbirligi: Isbirligi) -> None:
    """Her Takip eylemi eşleşmenin aktivitesini tazeler; Canlılık bunu okuyacak."""
    isbirligi.eslesme.son_aktivite_tarihi = _simdi()


def plan_gecisini_uygula(isbirligi: Isbirligi, olay: str, rol: str) -> PlanSonucu:
    """Kuralı sorar, sonucu modele yazar. 409 kural dışı, 403 taraf olmayan rol."""
    mevcut = PlanDurumu(
        isbirligi.durum,
        genc_onayi=isbirligi.genc_plan_onayi is not None,
        kurum_onayi=isbirligi.kurum_plan_onayi is not None,
    )
    try:
        sonuc = plan_gecisi(mevcut, olay, rol, milestone_sayisi=len(isbirligi.milestonelar))
    except GecersizTakipGecisi as hata:
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    except RolUygunDegil as hata:
        raise HTTPException(
            status_code=403, detail="Bu işlemi yalnızca iki taraf yapabilir."
        ) from hata
    if not sonuc.degisti:
        return sonuc
    simdi = _simdi()
    isbirligi.durum = sonuc.durum.durum
    isbirligi.genc_plan_onayi = (
        (isbirligi.genc_plan_onayi or simdi) if sonuc.durum.genc_onayi else None
    )
    isbirligi.kurum_plan_onayi = (
        (isbirligi.kurum_plan_onayi or simdi) if sonuc.durum.kurum_onayi else None
    )
    return sonuc


def plani_yaz(isbirligi: Isbirligi, adimlar: list[takip.AdimOnerisi]) -> None:
    """Ajanın önerisini plan yapar: eski adımlar silinir, onaylar sıfırlanır."""
    baslangic = isbirligi.baslangic_tarihi or dt.date.today()
    isbirligi.milestonelar.clear()
    for sira, adim in enumerate(adimlar):
        isbirligi.milestonelar.append(
            Milestone(
                baslik=adim.baslik.strip(),
                aciklama=adim.aciklama.strip(),
                sira=sira,
                hedef_tarih=takip.hedef_tarihi(baslangic, adim.hafta),
                durum=MILESTONE_BEKLIYOR,
            )
        )
    isbirligi.plan_onerildi_mi = True
    isbirligi.genc_plan_onayi = None
    isbirligi.kurum_plan_onayi = None


def detay(isbirligi: Isbirligi, hesap: Hesap, bugun: dt.date | None = None) -> IsbirligiDetayi:
    # eslestirme.py bu modülü yalnızca fonksiyon içinde içe aktarıyor; döngü yok.
    from app.api.eslestirme import iletisim

    bugun = bugun or dt.date.today()
    eslesme = isbirligi.eslesme
    adimlar = [
        MilestoneYaniti(
            id=m.id,
            sira=m.sira,
            baslik=m.baslik,
            aciklama=m.aciklama,
            hedef_tarih=m.hedef_tarih,
            durum=m.durum,
            genc_isaret=m.genc_isaret,
            kurum_isaret=m.kurum_isaret,
            kanit_linki=m.kanit_linki,
            gecikmis=gecikmis_mi(m.hedef_tarih, m.durum == MILESTONE_TAMAMLANDI, bugun),
        )
        for m in sorted(isbirligi.milestonelar, key=lambda m: m.sira)
    ]
    return IsbirligiDetayi(
        id=isbirligi.id,
        durum=isbirligi.durum,
        baslangic_tarihi=isbirligi.baslangic_tarihi,
        tamamlanma_tarihi=isbirligi.tamamlanma_tarihi,
        eslesme_id=eslesme.id,
        yetenek_karti_id=eslesme.yetenek_karti_id,
        ihtiyac_karti_id=eslesme.ihtiyac_karti_id,
        genc_adi=eslesme.yetenek_karti.kullanici.ad,
        kurum_adi=eslesme.ihtiyac_karti.kurum.ad,
        rol_alani=eslesme.yetenek_karti.rol_alani,
        problem_tanimi=eslesme.ihtiyac_karti.problem_tanimi,
        basari_kriteri=eslesme.ihtiyac_karti.basari_kriteri,
        genc_plan_onayi=isbirligi.genc_plan_onayi,
        kurum_plan_onayi=isbirligi.kurum_plan_onayi,
        plan_onerildi_mi=isbirligi.plan_onerildi_mi,
        milestonelar=adimlar,
        ilerleme=Ilerleme(
            tamamlanan=sum(a.durum == MILESTONE_TAMAMLANDI for a in adimlar),
            toplam=len(adimlar),
            geciken=sum(a.gecikmis for a in adimlar),
        ),
        durum_ozeti=isbirligi.durum_ozeti,
        ozet_tarihi=isbirligi.ozet_tarihi,
        iletisim=iletisim(eslesme, hesap),
    )


async def _ajana_sor(isbirligi: Isbirligi) -> list[takip.AdimOnerisi] | None:
    eslesme = isbirligi.eslesme
    return await takip.plan_oner(
        eslesme.ihtiyac_karti, eslesme.yetenek_karti, eslesme.ihtiyac_karti.kurum.ad
    )


# --- Uç noktalar ----------------------------------------------------------------------


@router.post("/{isbirligi_id}/plan-oner", response_model=IsbirligiDetayi)
async def plan_oner(
    isbirligi_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC, ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> IsbirligiDetayi:
    """Ajandan (yeniden) plan ister. Yalnızca `plan_bekliyor`'da; mevcut adımları
    siler ve iki onayı sıfırlar (arayüz önce sorar). LLM yanıt vermezse plan
    olduğu gibi kalır: 429 hız sınırı / 503 arıza, kurala uymayan çıktıda 503."""
    isbirligi, rol = await yazilabilir_isbirligi(oturum, hesap, isbirligi_id)
    plan_gecisini_uygula(isbirligi, PLAN_DUZENLE, rol)
    adimlar = await _ajana_sor(isbirligi)
    if adimlar is None:
        raise HTTPException(status_code=503, detail=PLAN_ONERILEMEDI)
    plani_yaz(isbirligi, adimlar)
    aktivite(isbirligi)
    bildirim_ekle(
        oturum,
        taraf_hesabi(isbirligi, karsi_rol(rol)),
        TUR_PLAN_DUZENLENDI,
        f"{taraf_adi(isbirligi, rol)} ajandan yeni bir plan istedi; son hâli onayını bekliyor.",
        isbirligi.eslesme_id,
    )
    await oturum.commit()
    return detay(isbirligi, hesap)


async def plani_arka_planda_oner(isbirligi_id: uuid.UUID) -> None:
    """Genç kabul edince planı yanıt gönderildikten sonra önerir (§ 4).

    Eşleştirme'nin arka plan işiyle aynı desen: kendi oturumu, hata yutulur.
    Plan önerilmediyse (LLM yok ya da çıktı kurala uymadı) iş birliği planı
    boş kalır; taraflar sayfadan "Plan öner" diyebilir ya da elle ekleyebilir.
    Tarafların eline geçmiş bir planı ezmez.
    """
    async with get_sessionmaker()() as oturum:
        try:
            isbirligi = await isbirligini_getir(oturum, isbirligi_id, kilitle=True)
            if (
                isbirligi is None
                or isbirligi.durum != ISBIRLIGI_PLAN_BEKLIYOR
                or isbirligi.plan_onerildi_mi
                or isbirligi.milestonelar
            ):
                return
            adimlar = await _ajana_sor(isbirligi)
            if adimlar is None:
                return
            plani_yaz(isbirligi, adimlar)
            for rol in (ROL_GENC, ROL_KURUM):
                bildirim_ekle(
                    oturum,
                    taraf_hesabi(isbirligi, rol),
                    TUR_PLAN_ONERILDI,
                    f"{taraf_adi(isbirligi, karsi_rol(rol))} ile iş birliğin için bir plan "
                    "önerildi; gözden geçir ve onayla.",
                    isbirligi.eslesme_id,
                )
            await oturum.commit()
        except Exception:
            logger.exception("Arka plan plan önerisi başarısız (%s)", isbirligi_id)
