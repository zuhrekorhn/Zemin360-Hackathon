"""İstekten hesabı bulan FastAPI bağımlılıkları (docs/faz-b-kimlik-ve-dongu.md § 1, § 3).

    mevcut_hesap            — geçerli token yoksa 401
    rol_gerekli("kurum")    — rol uymuyorsa 403
    bulunamadi(mesaj)       — başkasının kaynağı 404

Sahiplik bu bağımlılıkların işi değil; kaynağı okuyan uç nokta, kaynağın sahibini
`app/servisler/sahiplik.py`'ye sorar ve "göremez" kararını `bulunamadi` ile 404'e
çevirir (403 değil: kaynağın var olduğu sızmasın).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.kimlik import TokenGecersiz, token_coz
from app.db.session import get_session
from app.models.hesap import Hesap

GIRIS_GEREKLI = "Bu işlem için giriş gerekiyor."
OTURUM_GECERSIZ = "Oturumun süresi dolmuş; yeniden giriş gerekiyor."
ROL_UYGUN_DEGIL = "Bu işlem bu hesap türü için değil."

# auto_error=False: başlık yoksa FastAPI'nin İngilizce 403'ü yerine kendi 401'imiz.
_bearer = HTTPBearer(auto_error=False)


def _yetkisiz(mesaj: str) -> HTTPException:
    return HTTPException(status_code=401, detail=mesaj, headers={"WWW-Authenticate": "Bearer"})


async def mevcut_hesap(
    kimlik: HTTPAuthorizationCredentials | None = Depends(_bearer),
    oturum: AsyncSession = Depends(get_session),
) -> Hesap:
    """Bearer token'dan hesabı bulur; token yoksa, geçersizse ya da hesap yoksa 401."""
    if kimlik is None:
        raise _yetkisiz(GIRIS_GEREKLI)
    try:
        icerik = token_coz(kimlik.credentials)
    except TokenGecersiz as hata:
        raise _yetkisiz(OTURUM_GECERSIZ) from hata

    hesap = await oturum.scalar(
        select(Hesap)
        .options(selectinload(Hesap.kullanici), selectinload(Hesap.kurum))
        .where(Hesap.id == icerik.hesap_id)
    )
    # Rol token'dakiyle aynı olmalı: token'ı rol değişmeden önce almış biri
    # eski rolün yetkisini taşımasın.
    if hesap is None or hesap.rol != icerik.rol:
        raise _yetkisiz(OTURUM_GECERSIZ)
    return hesap


def rol_gerekli(*roller: str) -> Callable[..., Awaitable[Hesap]]:
    """Yalnızca verilen rollerdeki hesabı geçiren bağımlılık; diğerlerine 403."""

    async def bagimlilik(hesap: Hesap = Depends(mevcut_hesap)) -> Hesap:
        if hesap.rol not in roller:
            raise HTTPException(status_code=403, detail=ROL_UYGUN_DEGIL)
        return hesap

    return bagimlilik


def bulunamadi(mesaj: str) -> HTTPException:
    """Başkasının ya da var olmayan kaynağın hatası: ikisi ayırt edilmez."""
    return HTTPException(status_code=404, detail=mesaj)
