"""GİRVAK gözlem paneli ucu (docs/plans/dogrulama-iyilestirme.md § 10.3, § 14.4).

Yalnızca GİRVAK, yalnızca okuma. İki görünüm: platform bazında kanıt erişim
dağılımı ve kalıcı dış servis sağlığı (+ değerlendirme süresi / token özeti).
Kayıtlar kişi ve adres taşımaz.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.kimlik import rol_gerekli
from app.core.dis_servisler import servis_kipleri
from app.db.session import get_session
from app.models.gozlem import SAKLAMA_GUN
from app.models.hesap import ROL_GIRVAK
from app.schemas.gozlem import (
    DegerlendirmeOzetiYaniti,
    GozlemYaniti,
    PlatformErisimiYaniti,
    ServisDurumuYaniti,
)
from app.servisler import gozlem

router = APIRouter(
    prefix="/girvak/gozlem",
    tags=["girvak"],
    dependencies=[Depends(rol_gerekli(ROL_GIRVAK))],
)

VARSAYILAN_GUN = 30


def _servis_yaniti(
    servis: str, kip: str | None, durum: gozlem.ServisDurumu | None
) -> ServisDurumuYaniti:
    if durum is None:
        return ServisDurumuYaniti(
            servis=servis,
            kip=kip,
            basari_sayisi=0,
            hata_sayisi=0,
            son_basari=None,
            son_hata=None,
            son_hata_turu=None,
        )
    return ServisDurumuYaniti(
        servis=servis,
        kip=kip,
        basari_sayisi=durum.basari_sayisi,
        hata_sayisi=durum.hata_sayisi,
        son_basari=durum.son_basari,
        son_hata=durum.son_hata,
        son_hata_turu=durum.son_hata_turu,
    )


@router.get("", response_model=GozlemYaniti)
async def gozlem_paneli(
    gun: int = Query(default=VARSAYILAN_GUN, ge=1, le=SAKLAMA_GUN),
    oturum: AsyncSession = Depends(get_session),
) -> GozlemYaniti:
    """Son `gun` günün erişim dağılımı, servis sağlığı ve değerlendirme özeti."""
    simdi = dt.datetime.now(dt.UTC)
    bas = simdi - dt.timedelta(days=gun)
    kipler = servis_kipleri()
    durumlar = {d.servis: d for d in await gozlem.servis_durumlari(oturum, bas.date())}
    # Kaydı olmayan servis de görünür (0 çağrı): "hiç çağrılmadı" bir bilgidir.
    servisler = [
        _servis_yaniti(servis, kipler.get(servis), durumlar.get(servis))
        for servis in [*kipler, *(s for s in durumlar if s not in kipler)]
    ]
    ozet = await gozlem.degerlendirme_ozeti(oturum, bas)
    return GozlemYaniti(
        gun=gun,
        erisim=[
            PlatformErisimiYaniti(
                platform=p.platform,
                toplam=p.toplam,
                erisimler=p.erisimler,
                acik_orani=round(p.acik_orani, 3),
            )
            for p in await gozlem.platform_erisimi(oturum, bas)
        ],
        servisler=servisler,
        degerlendirme=DegerlendirmeOzetiYaniti(
            sayi=ozet.sayi,
            ortalama_sure_ms=ozet.ortalama_sure_ms,
            girdi_token=ozet.girdi_token,
            cikti_token=ozet.cikti_token,
        ),
    )
