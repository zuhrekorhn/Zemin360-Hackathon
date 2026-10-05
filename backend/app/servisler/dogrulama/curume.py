"""Link çürümesi yoklaması (plan § 10.4): Canlılık taramasının bir adımı.

Kurallar saf (`app/agents/dogrulama/curume.py`); burada linkin yeniden açılması
ve sonucun modele yazılması. Yoklama modeli çağırmaz; yalnızca eşiği geçen
(ya da toparlanan) çalışma yeniden değerlendirilir. Çürüyen parçanın önceki
puanı parçanın `belge["curume"]` kaydında saklanır (puan geçmişi). Commit
çağıranın işi.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dogrulama.curume import curumus_mu, sayac_gecisi, yoklanacak_mi
from app.api.bildirimler import bildirim_ekle
from app.core.kanit_okuma import kaniti_oku
from app.core.kanit_okuma.belge import ErisimDurumu, ParcaTuru
from app.models.bildirim import TUR_KANIT_CURUDU
from app.models.gozlem import KAYNAK_YOKLAMA
from app.models.kanit_parcasi import KanitParcasi
from app.models.somut_cikti import SomutCikti
from app.servisler import gozlem
from app.servisler.dogrulama.kanit import degerlendir
from app.servisler.dogrulama.parcalar import gostergeyi_yeniden_degerlendirmeye_al
from app.servisler.dogrulama.sorgular import cikti_getir, gencin_hesap_id

logger = logging.getLogger("zemin360.dogrulama")

# Bir taramada en çok bu kadar link yoklanır, en uzun süredir bakılmayan önce.
TARAMA_BASINA_EN_COK = 100
ESZAMANLI_YOKLAMA = 5

CURUME_BILDIRIMI = (
    "“{baslik}” çalışmandaki kanıt linki art arda üç kontrolde açılmadı; silinmiş ya da "
    "gizlenmiş olabilir. Kanıt başlığı şimdilik boş. Linki düzeltir ya da yeni bir kanıt "
    "eklersen gösterge yeniden hesaplanır."
)

ErisimOkuyucu = Callable[[str], Awaitable[ErisimDurumu]]


@dataclass(frozen=True)
class CurumeSonucu:
    yoklanan: int = 0
    curuyen: int = 0
    iyilesen: int = 0
    hatali: int = 0


async def erisimi_oku(url: str) -> ErisimDurumu:
    """Yalnızca erişim durumu: yedek okuyucu ve model yok (ucuz yoklama)."""
    return (await kaniti_oku(url)).erisim


def _son_yoklama(parca: KanitParcasi) -> dt.datetime | None:
    ham = (parca.belge or {}).get("yoklama_tarihi")
    return dt.datetime.fromisoformat(ham) if ham else None


def _isleme_bekliyor(parca: KanitParcasi) -> bool:
    """Eşik geçilmiş ama bildirim ve yeniden değerlendirme henüz yapılmamış."""
    return curumus_mu(parca.curume_sayaci or 0) and "curume" not in (parca.belge or {})


async def _okuyabildigi(oku: ErisimOkuyucu, url: str) -> ErisimDurumu:
    try:
        return await oku(url)
    except Exception:  # zarif düşüş: geçici arıza sayılmaz, bir sonraki taramada yeniden
        logger.warning("link yoklamasi okunamadi", exc_info=True)
        return ErisimDurumu.HATA


async def curume_yoklamasi(
    oturum: AsyncSession,
    simdi: dt.datetime,
    oku: ErisimOkuyucu | None = None,
) -> CurumeSonucu:
    oku = oku or erisimi_oku  # çağrı anında çözülür: testler modül işlevini değiştirebilir
    adaylar = list(
        await oturum.scalars(
            select(KanitParcasi).where(
                KanitParcasi.tur == ParcaTuru.LINK.value,
                KanitParcasi.url.isnot(None),
                or_(KanitParcasi.erisim == ErisimDurumu.ACIK.value, KanitParcasi.curume_sayaci > 0),
            )
        )
    )
    yoklanacaklar = sorted(
        (
            p
            for p in adaylar
            if yoklanacak_mi(
                p.erisim,
                p.curume_sayaci or 0,
                _son_yoklama(p),
                simdi,
                isleme_bekliyor=_isleme_bekliyor(p),
            )
        ),
        key=lambda p: _son_yoklama(p) or dt.datetime.min.replace(tzinfo=dt.UTC),
    )[:TARAMA_BASINA_EN_COK]
    if not yoklanacaklar:
        return CurumeSonucu()

    sinir = asyncio.Semaphore(ESZAMANLI_YOKLAMA)

    async def tek(parca: KanitParcasi) -> tuple[ErisimDurumu, int]:
        async with sinir:
            baslangic = time.perf_counter()
            erisim = await _okuyabildigi(oku, parca.url)
            return erisim, round((time.perf_counter() - baslangic) * 1000)

    sonuclar = await asyncio.gather(*(tek(p) for p in yoklanacaklar))

    # Kalem başına bir kez yeniden değerlendirilir: eşiği geçen ya da toparlanan.
    degisenler: dict[uuid.UUID, list[KanitParcasi]] = {}
    for parca, (erisim, sure_ms) in zip(yoklanacaklar, sonuclar, strict=True):
        gozlem.kanit_okuma_ekle(
            oturum,
            kaynak=KAYNAK_YOKLAMA,
            platform=parca.platform,
            okuyucu="dogrudan",
            erisim=erisim.value,
            seviye=parca.seviye,
            sure_ms=sure_ms,
        )
        parca.curume_sayaci = sayac_gecisi(parca.curume_sayaci or 0, erisim)
        parca.belge = {**(parca.belge or {}), "yoklama_tarihi": simdi.isoformat()}
        curumus = curumus_mu(parca.curume_sayaci)
        isleniyor = "curume" in parca.belge
        if curumus != isleniyor:
            degisenler.setdefault(parca.somut_cikti_id, []).append(parca)
    await oturum.flush()

    curuyen = iyilesen = hatali = 0
    for cikti_id, parcalar in degisenler.items():
        try:
            async with oturum.begin_nested():
                c, i = await _kalemi_isle(oturum, cikti_id, parcalar, simdi)
            curuyen += c
            iyilesen += i
        except Exception:  # LLM ya da ağ arızası taramayı düşürmez; sonraki taramada denenir
            logger.warning("curume degerlendirmesi basarisiz", exc_info=True)
            hatali += 1
    return CurumeSonucu(len(yoklanacaklar), curuyen, iyilesen, hatali)


async def _kalemi_isle(
    oturum: AsyncSession, cikti_id: uuid.UUID, parcalar: list[KanitParcasi], simdi: dt.datetime
) -> tuple[int, int]:
    """Çürüyen parçaların geçmişini saklar, iyileşenlerin kaydını siler, kalemi
    yeniden değerlendirir ve (yalnızca çürüme için) gence bildirir."""
    cikti = await cikti_getir(oturum, cikti_id)
    curuyen = iyilesen = 0
    for parca in parcalar:
        belge = dict(parca.belge or {})
        if curumus_mu(parca.curume_sayaci):
            belge["curume"] = {"tarih": simdi.isoformat(), "onceki_puanlar": _puanlar(cikti)}
            curuyen += 1
        else:
            belge.pop("curume", None)
            iyilesen += 1
        parca.belge = belge
    gostergeyi_yeniden_degerlendirmeye_al(cikti)
    await degerlendir(oturum, cikti)
    if curuyen:
        hesap_id = await gencin_hesap_id(oturum, cikti.yetenek_karti_id)
        bildirim_ekle(
            oturum, hesap_id, TUR_KANIT_CURUDU, CURUME_BILDIRIMI.format(baslik=cikti.baslik)
        )
    return curuyen, iyilesen


def _puanlar(cikti: SomutCikti) -> dict[str, int | None]:
    skor = cikti.guven_skoru
    if skor is None:
        return {}
    return {
        "kanit": skor.kanit_orijinalligi,
        "sonuc": skor.sonuc_olculebilirligi,
        "rol": skor.rol_netligi,
    }
