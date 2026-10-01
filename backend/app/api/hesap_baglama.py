"""Hesap bağlama uçları (docs/plans/dogrulama-iyilestirme.md § 6).

Yalnızca genç. Orkestrasyon `app/servisler/hesap_baglama.py`'de; burada şema,
sahiplik ve hata çevirisi. Bağlantı değişince linkli çalışmalar yanıttan sonra
arka planda yeniden okunur.
"""

from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.kimlik import rol_gerekli
from app.db.session import get_session
from app.models.hesap import ROL_GENC, Hesap
from app.schemas.hesap_baglama import (
    BagliHesapYaniti,
    HesaplarimYaniti,
    OAuthBaslatYaniti,
    OAuthTamamlaIstegi,
)
from app.servisler import hesap_baglama, kart_hazirlama
from app.servisler.genc_karti import gencin_karti

router = APIRouter(prefix="/hesap-baglama", tags=["hesap bağlama"])

SAGLAYICI_KAPALI = "Bu hesap türü şu an bağlanamıyor."
DURUM_GECERSIZ = "Bağlantının süresi doldu. Hesabını bağlamayı yeniden başlat."
REDDEDILDI = "Hesabın bağlanamadı. Yeniden dene."
BASKASINA_BAGLI = "Bu hesap başka bir kullanıcıya bağlı."
ULASILAMADI = "Şu an bağlantı kuramadık. Birkaç dakika sonra yeniden dene."
BULUNAMADI = "Bağlı hesap bulunamadı."


async def _yeniden_okumayi_planla(
    oturum: AsyncSession, hesap: Hesap, arka_plan: BackgroundTasks
) -> None:
    kart = await gencin_karti(oturum, hesap.kullanici.id)
    if kart is not None:
        arka_plan.add_task(kart_hazirlama.kalemleri_yeniden_oku, kart.id)


@router.get("", response_model=HesaplarimYaniti)
async def hesaplarim(
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)), oturum: AsyncSession = Depends(get_session)
) -> HesaplarimYaniti:
    hesaplar = await hesap_baglama.bagli_hesaplar(oturum, hesap.kullanici.id)
    return HesaplarimYaniti(
        hesaplar=[BagliHesapYaniti.model_validate(h) for h in hesaplar],
        oauth_saglayicilari=hesap_baglama.acik_oauth_saglayicilari(),
    )


@router.post("/oauth/{saglayici}/baslat", response_model=OAuthBaslatYaniti)
async def oauth_baslat(
    saglayici: str, hesap: Hesap = Depends(rol_gerekli(ROL_GENC))
) -> OAuthBaslatYaniti:
    try:
        return OAuthBaslatYaniti(yetki_adresi=hesap_baglama.oauth_baslat(hesap.id, saglayici))
    except hesap_baglama.SaglayiciKapali as hata:
        raise HTTPException(status_code=404, detail=SAGLAYICI_KAPALI) from hata


@router.post("/oauth/{saglayici}/tamamla", response_model=BagliHesapYaniti, status_code=201)
async def oauth_tamamla(
    saglayici: str,
    istek: OAuthTamamlaIstegi,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> BagliHesapYaniti:
    """Durum geçersizse ya da sağlayıcı kodu reddederse 400; hesap başkasındaysa 409;
    sağlayıcıya ulaşılamazsa 503. Aynı hesabın yeniden bağlanması yan etkisiz."""
    try:
        bagli = await hesap_baglama.oauth_tamamla(
            oturum,
            hesap_id=hesap.id,
            kullanici_id=hesap.kullanici.id,
            saglayici=saglayici,
            kod=istek.kod,
            durum=istek.durum,
        )
    except hesap_baglama.SaglayiciKapali as hata:
        raise HTTPException(status_code=404, detail=SAGLAYICI_KAPALI) from hata
    except hesap_baglama.DurumGecersiz as hata:
        raise HTTPException(status_code=400, detail=DURUM_GECERSIZ) from hata
    except hesap_baglama.BaglantiReddedildi as hata:
        raise HTTPException(status_code=400, detail=REDDEDILDI) from hata
    except hesap_baglama.BaskasinaBagli as hata:
        raise HTTPException(status_code=409, detail=BASKASINA_BAGLI) from hata
    except (TimeoutError, httpx.HTTPError) as hata:
        raise HTTPException(status_code=503, detail=ULASILAMADI) from hata
    await oturum.commit()
    await _yeniden_okumayi_planla(oturum, hesap, arka_plan)
    return BagliHesapYaniti.model_validate(bagli)


@router.delete("/{bagli_hesap_id}", status_code=204)
async def baglantiyi_kaldir(
    bagli_hesap_id: uuid.UUID,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> Response:
    """Başkasının bağlantısı 404 (varlık sızmasın)."""
    try:
        await hesap_baglama.baglantiyi_kaldir(oturum, hesap.kullanici.id, bagli_hesap_id)
    except hesap_baglama.BagliHesapBulunamadi as hata:
        raise HTTPException(status_code=404, detail=BULUNAMADI) from hata
    await oturum.commit()
    await _yeniden_okumayi_planla(oturum, hesap, arka_plan)
    return Response(status_code=204)
