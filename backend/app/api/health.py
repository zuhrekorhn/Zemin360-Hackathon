import datetime as dt

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.kimlik import rol_gerekli
from app.core.dis_servisler import servis_kipleri
from app.core.dis_servisler.saglik import SAGLIK
from app.models.hesap import ROL_GIRVAK

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


class ServisSagligi(BaseModel):
    servis: str
    kip: str
    basari_sayisi: int
    hata_sayisi: int
    son_basari: dt.datetime | None
    son_hata: dt.datetime | None
    son_hata_turu: str | None


@router.get(
    "/saglik/servisler",
    response_model=list[ServisSagligi],
    dependencies=[Depends(rol_gerekli(ROL_GIRVAK))],
)
async def servis_sagligi() -> list[ServisSagligi]:
    """Dış servislerin kipi ve süreç başından beri sonuçları (docs/dogrulama.md § 14.4). Yalnızca
    GİRVAK."""
    return [
        ServisSagligi(servis=servis, kip=kip, **vars(SAGLIK.oku(servis)))
        for servis, kip in servis_kipleri().items()
    ]
