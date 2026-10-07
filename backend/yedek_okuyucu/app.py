"""Yedek okuyucu servisi: backend'in okuyamadığı sayfayı tarayıcıda açar (docs/dogrulama.md § 5.1,
§ 5.5).

    POST /oku     {"url", "ekran": "her_zaman" | "metin_azsa" | "hayir", "en_az_metin"}
                  → {"durum", "son_url", "html", "ekran_goruntuleri": [base64 JPEG], "hata"}
    GET  /saglik  → {"durum": "ok"}

Backend'den ayrı bir süreç. Tek dış bağımlılığı backend'in SSRF kuralları
(`app/core/guvenli_istek.py`); kurallar iki yerde yazılmasın diye o dosya
import edilir.
`YEDEK_OKUYUCU_ANAHTARI` doluysa istek `Authorization: Bearer <anahtar>` ister.
"""

from __future__ import annotations

import base64
import hmac
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from yedek_okuyucu.sayfa_acici import EkranKurali, SayfaAcici
from yedek_okuyucu.vekil import SuzgecliVekil

logger = logging.getLogger("zemin360.yedek_okuyucu")

ANAHTAR = os.environ.get("YEDEK_OKUYUCU_ANAHTARI", "")
ESZAMANLI = int(os.environ.get("YEDEK_OKUYUCU_ESZAMANLI", "2"))


@asynccontextmanager
async def omur(uygulama: FastAPI):
    if not ANAHTAR:
        logger.warning("YEDEK_OKUYUCU_ANAHTARI bos: servis anahtarsiz istek kabul ediyor")
    vekil = SuzgecliVekil()
    await vekil.baslat()
    acici = SayfaAcici(vekil.port, ESZAMANLI)
    await acici.baslat()
    uygulama.state.acici = acici
    try:
        yield
    finally:
        await acici.durdur()
        await vekil.durdur()


app = FastAPI(title="Zemin360 yedek okuyucu", lifespan=omur)


class OkumaIstegi(BaseModel):
    url: str = Field(max_length=2048)
    ekran: EkranKurali = EkranKurali.METIN_AZSA
    en_az_metin: int = Field(default=200, ge=0, le=100_000)


def _yetkili_mi(authorization: str | None) -> bool:
    if not ANAHTAR:
        return True
    return hmac.compare_digest(authorization or "", f"Bearer {ANAHTAR}")


@app.post("/oku")
async def oku(istek: OkumaIstegi, authorization: str | None = Header(default=None)) -> dict:
    if not _yetkili_mi(authorization):
        raise HTTPException(401, "anahtar gecersiz")
    acilis = await app.state.acici.ac(istek.url, istek.ekran, istek.en_az_metin)
    return {
        "durum": acilis.durum,
        "son_url": acilis.son_url,
        "html": acilis.html,
        "ekran_goruntuleri": [base64.b64encode(g).decode() for g in acilis.ekran_goruntuleri],
        "hata": acilis.hata.value if acilis.hata else None,
    }


@app.get("/saglik")
async def saglik() -> dict:
    return {"durum": "ok"}
