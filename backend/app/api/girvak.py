"""GİRVAK paneli (docs/faz-b-kimlik-ve-dongu.md § 7).

Faz B'de yalnızca sayılar: hesap, kart, eşleşme, iş birliği. Hedefler ve
grafikler Faz D'de bu uca eklenecek. Kişisel veri dönmez, yalnızca sayım.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.eslestirme import (
    DURUM_ILGILENILIYOR,
    DURUM_KABUL_EDILDI,
    DURUM_ONERILDI,
    DURUM_REDDEDILDI,
)
from app.api.kimlik import rol_gerekli
from app.db.session import get_session
from app.models.eslesme import Eslesme
from app.models.hesap import ROL_GENC, ROL_GIRVAK, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.isbirligi import Isbirligi
from app.models.yetenek_karti import YetenekKarti
from app.schemas.girvak import EslesmeSayilari, HesapSayilari, Sayilar

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
        ),
        isbirligi=await _say(oturum, Isbirligi),
    )
