"""Yerel depodaki kanıt dosyasının indirilmesi (plan § 4.4; yalnızca `DEPO_SAGLAYICI=yerel`).

Yetki token'dadır: imzalı adresi yalnızca dosyayı görmeye yetkili kullanıcı
alır (`app/api/dogrulama.py`), adres birkaç dakika geçerlidir. Bu yüzden uç
Bearer istemez; tarayıcı adresi doğrudan açabilir. Yanıt her zaman indirmedir,
sayfa olarak açılmaz (`nosniff`, `attachment`, kısıtlayıcı CSP). R2 kipinde
imzalı adres R2'ye gider, bu uç 404 döner.
"""

from __future__ import annotations

import jwt
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.core.dis_servisler import kurulum
from app.core.dis_servisler.depo import YerelDepo, indirme_basligi

router = APIRouter(prefix="/dosya", tags=["dosya"])

_GECERSIZ = "Bu indirme bağlantısının süresi dolmuş. Sayfayı yenileyip yeniden dene."


@router.get("/{token}")
async def dosyayi_indir(token: str) -> Response:
    depo = kurulum.depo()
    if not isinstance(depo, YerelDepo):
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    try:
        anahtar, dosya_adi, icerik_turu = depo.token_coz(token)
        veri = await depo.al(anahtar)
    except (jwt.InvalidTokenError, KeyError, ValueError) as hata:
        raise HTTPException(status_code=404, detail=_GECERSIZ) from hata
    except FileNotFoundError as hata:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.") from hata
    return Response(
        content=veri,
        media_type=icerik_turu,
        headers={
            "Content-Disposition": indirme_basligi(dosya_adi),
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "Cache-Control": "private, no-store",
        },
    )
