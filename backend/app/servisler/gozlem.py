"""Doğrulamanın kalıcı gözlemi (plan § 10.3, § 14.4): yazma ve okuma.

Kayıtlar kişi ve adres taşımaz (`app/models/gozlem.py`). Kanıt okuma ve
değerlendirme kayıtları çağıranın işlemine eklenir (commit çağıranın işi);
dış servis günlüğü kendi kısa işlemini açar ve hatayı yutar: gözlem hiçbir
akışı düşürmemeli.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dogrulama.gozlem import PlatformErisimi, erisim_dagilimi, servis_adi
from app.core.dis_servisler.saglik import SAGLIK
from app.db.session import get_sessionmaker
from app.models.gozlem import (
    SAKLAMA_GUN,
    DegerlendirmeGozlemi,
    KanitGozlemi,
    ServisGunlugu,
)

logger = logging.getLogger("zemin360.gozlem")


def kanit_okuma_ekle(
    oturum: AsyncSession,
    *,
    kaynak: str,
    platform: str | None,
    okuyucu: str,
    erisim: str,
    seviye: str | None = None,
    sure_ms: int | None = None,
    girdi_ozeti: str | None = None,
) -> None:
    oturum.add(
        KanitGozlemi(
            kaynak=kaynak,
            platform=platform or "web",
            okuyucu=okuyucu,
            erisim=erisim,
            seviye=seviye,
            sure_ms=sure_ms,
            girdi_ozeti=girdi_ozeti,
        )
    )


def degerlendirme_ekle(
    oturum: AsyncSession,
    *,
    girdi_ozeti: str | None,
    parca_sayisi: int,
    sure_ms: int,
    model_cagrisi: int,
    girdi_token: int,
    cikti_token: int,
) -> None:
    oturum.add(
        DegerlendirmeGozlemi(
            girdi_ozeti=girdi_ozeti,
            parca_sayisi=parca_sayisi,
            sure_ms=sure_ms,
            model_cagrisi=model_cagrisi,
            girdi_token=girdi_token,
            cikti_token=cikti_token,
        )
    )


# --- Dış servis günlüğü ---------------------------------------------------------------------


async def servis_olayi_yaz(servis: str, basari: bool, hata_turu: str | None = None) -> None:
    """Günlük sayaca bir çağrı ekler; kendi işlemini açar, hata taşımaz."""
    simdi = dt.datetime.now(dt.UTC)
    deger = {
        "servis": servis,
        "gun": simdi.date(),
        "basari_sayisi": 1 if basari else 0,
        "hata_sayisi": 0 if basari else 1,
        "son_basari": simdi if basari else None,
        "son_hata": None if basari else simdi,
        "son_hata_turu": None if basari else hata_turu,
    }
    guncelle = {
        "basari_sayisi": ServisGunlugu.basari_sayisi + deger["basari_sayisi"],
        "hata_sayisi": ServisGunlugu.hata_sayisi + deger["hata_sayisi"],
    }
    if basari:
        guncelle["son_basari"] = simdi
    else:
        guncelle["son_hata"] = simdi
        guncelle["son_hata_turu"] = hata_turu
    try:
        async with get_sessionmaker()() as oturum:
            await oturum.execute(
                insert(ServisGunlugu)
                .values(**deger)
                .on_conflict_do_update(
                    index_elements=[ServisGunlugu.servis, ServisGunlugu.gun], set_=guncelle
                )
            )
            await oturum.commit()
    except Exception:
        logger.warning("servis gunlugu yazilamadi", exc_info=True)


_ARKA_PLAN: set[asyncio.Task] = set()


def _kalici_yaz(servis: str, basari: bool, hata_turu: str | None) -> None:
    """`SAGLIK` kancası: çağrıyı bekletmeden arka planda yazar."""
    try:
        gorev = asyncio.get_running_loop().create_task(servis_olayi_yaz(servis, basari, hata_turu))
    except RuntimeError:  # çalışan döngü yok (senkron bağlam): yazılmaz
        return
    _ARKA_PLAN.add(gorev)
    gorev.add_done_callback(_ARKA_PLAN.discard)


def kalici_saglik_ac() -> None:
    """Uygulama açılışında çağrılır; testlerde çağrılmaz (veritabanına yazmasın)."""
    SAGLIK.kalici = _kalici_yaz


# --- Okuma (GİRVAK paneli) ------------------------------------------------------------------


@dataclass(frozen=True)
class ServisDurumu:
    servis: str
    basari_sayisi: int
    hata_sayisi: int
    son_basari: dt.datetime | None
    son_hata: dt.datetime | None
    son_hata_turu: str | None


@dataclass(frozen=True)
class DegerlendirmeOzeti:
    sayi: int
    ortalama_sure_ms: int
    girdi_token: int
    cikti_token: int


async def platform_erisimi(oturum: AsyncSession, bas: dt.datetime) -> list[PlatformErisimi]:
    satirlar = await oturum.execute(
        select(KanitGozlemi.platform, KanitGozlemi.erisim, func.count())
        .where(KanitGozlemi.tarih >= bas)
        .group_by(KanitGozlemi.platform, KanitGozlemi.erisim)
    )
    return erisim_dagilimi((p, e, n) for p, e, n in satirlar.all())


async def servis_durumlari(oturum: AsyncSession, bas: dt.date) -> list[ServisDurumu]:
    """Günlük satırlar servis adına göre toplanır (`oauth_github` → `oauth`)."""
    satirlar = await oturum.scalars(select(ServisGunlugu).where(ServisGunlugu.gun >= bas))
    toplam: dict[str, list[ServisGunlugu]] = defaultdict(list)
    for satir in satirlar:
        toplam[servis_adi(satir.servis)].append(satir)
    sonuc = []
    for servis, gunler in sorted(toplam.items()):
        son_hata = max((g for g in gunler if g.son_hata), key=lambda g: g.son_hata, default=None)
        sonuc.append(
            ServisDurumu(
                servis=servis,
                basari_sayisi=sum(g.basari_sayisi for g in gunler),
                hata_sayisi=sum(g.hata_sayisi for g in gunler),
                son_basari=max((g.son_basari for g in gunler if g.son_basari), default=None),
                son_hata=son_hata.son_hata if son_hata else None,
                son_hata_turu=son_hata.son_hata_turu if son_hata else None,
            )
        )
    return sonuc


async def degerlendirme_ozeti(oturum: AsyncSession, bas: dt.datetime) -> DegerlendirmeOzeti:
    sayi, sure, girdi, cikti = (
        await oturum.execute(
            select(
                func.count(),
                func.coalesce(func.avg(DegerlendirmeGozlemi.sure_ms), 0),
                func.coalesce(func.sum(DegerlendirmeGozlemi.girdi_token), 0),
                func.coalesce(func.sum(DegerlendirmeGozlemi.cikti_token), 0),
            ).where(DegerlendirmeGozlemi.tarih >= bas)
        )
    ).one()
    return DegerlendirmeOzeti(sayi, round(sure), int(girdi), int(cikti))


async def eski_gozlemleri_temizle(oturum: AsyncSession, simdi: dt.datetime) -> None:
    """Saklama süresini (90 gün) geçen kayıtlar silinir; Canlılık taramasında çalışır."""
    sinir = simdi - dt.timedelta(days=SAKLAMA_GUN)
    await oturum.execute(delete(KanitGozlemi).where(KanitGozlemi.tarih < sinir))
    await oturum.execute(delete(DegerlendirmeGozlemi).where(DegerlendirmeGozlemi.tarih < sinir))
    await oturum.execute(delete(ServisGunlugu).where(ServisGunlugu.gun < sinir.date()))
