"""GİRVAK paneli (docs/faz-b-kimlik-ve-dongu.md § 7).

Faz B'de yalnızca sayılar: hesap, kart, eşleşme, iş birliği. Hedefler ve
grafikler Faz D'de bu uca eklenecek. Kişisel veri dönmez, yalnızca sayım.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.eslestirme import (
    DURUM_GENC_ILGILENDI,
    DURUM_ILGILENILIYOR,
    DURUM_KABUL_EDILDI,
    DURUM_KAPANDI,
    DURUM_ONERILDI,
    DURUM_REDDEDILDI,
)
from app.agents.takip_durumu import (
    ISBIRLIGI_AKTIF,
    ISBIRLIGI_PLAN_BEKLIYOR,
    ISBIRLIGI_TAMAMLANDI,
)
from app.api.kimlik import rol_gerekli
from app.core.program import HEDEFLER
from app.db.session import get_session
from app.models.eslesme import Eslesme
from app.models.hesap import ROL_GENC, ROL_GIRVAK, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.isbirligi import Isbirligi
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.models.yetenek_karti import YetenekKarti
from app.schemas.girvak import (
    EslesmeSayilari,
    HedefSayisi,
    HesapSayilari,
    IsbirligiSayilari,
    KapananIhtiyaclar,
    Sayilar,
)
from app.servisler.ilgi import IHTIYAC_KAPANDI

router = APIRouter(prefix="/girvak", tags=["girvak"])


async def _say(oturum: AsyncSession, model) -> int:
    return await oturum.scalar(select(func.count()).select_from(model))


async def _gruplu(oturum: AsyncSession, kolon) -> dict[str, int]:
    satirlar = await oturum.execute(select(kolon, func.count()).group_by(kolon))
    return {deger: sayi for deger, sayi in satirlar.all()}


@router.get("/sayilar", response_model=Sayilar)
async def sayilar(
    _hesap: Hesap = Depends(rol_gerekli(ROL_GIRVAK)),
    oturum: AsyncSession = Depends(get_session),
) -> Sayilar:
    roller = await _gruplu(oturum, Hesap.rol)
    durumlar = await _gruplu(oturum, Eslesme.durum)
    isbirlikleri = await _gruplu(oturum, Isbirligi.durum)
    return Sayilar(
        hesap=HesapSayilari(
            genc=roller.get(ROL_GENC, 0),
            kurum=roller.get(ROL_KURUM, 0),
            girvak=roller.get(ROL_GIRVAK, 0),
        ),
        yetenek_karti=await _say(oturum, YetenekKarti),
        ihtiyac_karti=await _say(oturum, IhtiyacKarti),
        eslesme=EslesmeSayilari(
            onerildi=durumlar.get(DURUM_ONERILDI, 0),
            ilgileniliyor=durumlar.get(DURUM_ILGILENILIYOR, 0),
            kabul_edildi=durumlar.get(DURUM_KABUL_EDILDI, 0),
            reddedildi=durumlar.get(DURUM_REDDEDILDI, 0),
            genc_ilgilendi=durumlar.get(DURUM_GENC_ILGILENDI, 0),
            kapandi=durumlar.get(DURUM_KAPANDI, 0),
        ),
        isbirligi=await _say(oturum, Isbirligi),
        isbirligi_durumlari=IsbirligiSayilari(
            plan_bekliyor=isbirlikleri.get(ISBIRLIGI_PLAN_BEKLIYOR, 0),
            aktif=isbirlikleri.get(ISBIRLIGI_AKTIF, 0),
            tamamlandi=isbirlikleri.get(ISBIRLIGI_TAMAMLANDI, 0),
        ),
        hedefler=await hedef_sayilari(oturum, durumlar, isbirlikleri),
        kapanan_ihtiyaclar=await kapanan_ihtiyaclar(oturum),
    )


async def kapanan_ihtiyaclar(oturum: AsyncSession) -> KapananIhtiyaclar:
    satirlar = await oturum.execute(
        select(IhtiyacKarti.kapanma_nedeni, func.count())
        .where(IhtiyacKarti.durum == IHTIYAC_KAPANDI)
        .group_by(IhtiyacKarti.kapanma_nedeni)
    )
    nedenler = {neden or "nedensiz": sayi for neden, sayi in satirlar.all()}
    return KapananIhtiyaclar(**nedenler)


async def hedef_sayilari(
    oturum: AsyncSession, eslesme_durumlari: dict[str, int], isbirligi_durumlari: dict[str, int]
) -> list[HedefSayisi]:
    """Program hedefleri, platformdaki ölçümleriyle (docs/faz-d-canlilik.md § 7).

    Yalnızca hesabı olan profiller sayılır (Faz B öncesi profil programın
    katılımcısı değil).
    """
    basvuru = await oturum.scalar(
        select(func.count(func.distinct(YetenekKarti.kullanici_id)))
        .join(Kullanici, Kullanici.id == YetenekKarti.kullanici_id)
        .where(Kullanici.hesap_id.isnot(None))
    )
    kurum = await oturum.scalar(
        select(func.count(func.distinct(IhtiyacKarti.kurum_id)))
        .join(Kurum, Kurum.id == IhtiyacKarti.kurum_id)
        .where(Kurum.hesap_id.isnot(None))
    )
    sayilar = {
        "basvuru": basvuru,
        "kurum": kurum,
        "eslesme": eslesme_durumlari.get(DURUM_KABUL_EDILDI, 0),
        "pilot": isbirligi_durumlari.get(ISBIRLIGI_TAMAMLANDI, 0),
    }
    return [
        HedefSayisi(
            anahtar=h.anahtar,
            program_adi=h.program_adi,
            olcum=h.olcum,
            sayi=sayilar[h.anahtar],
            hedef=h.hedef,
        )
        for h in HEDEFLER
    ]
