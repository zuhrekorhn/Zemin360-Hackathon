"""Şüpheli referans yanıtı (plan § 9, bulgu 21): `referans_supheli`.

İzler `referans_istegi.yanit_isareti` JSONB'sinde (yeni tablo yok):
  - `istek_izi`: genç isteği açarken (oturum açmış gencin IP / tarayıcı özeti);
  - `form_acilis`: referans kişi formu ilk açtığında (GET);
  - `yanit_izi`, `form_suresi_sn`, `sinyaller`: yanıt gelince.
Gencin izleri, bütün referans isteklerindeki `istek_izi`'leridir (giriş
kaydı tutulmuyor; referans isteyen her an oturum açmış gencin bir girişidir).
İzler 90 gün sonra silinir (Canlılık taraması, `eski_izleri_temizle`);
sinyaller ve süre kalır. Kural `agents/dogrulama/referans_suphesi.py`'de.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dogrulama.referans_durumu import DURUM_BEKLIYOR, DURUM_YANITLANDI
from app.agents.dogrulama.referans_suphesi import iz_saklama_siniri, referans_sinyalleri
from app.core.istek_izi import IstekIzi
from app.models.inceleme_isareti import TUR_REFERANS_SUPHELI
from app.models.referans_istegi import ReferansIstegi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler import inceleme

IZ_ALANLARI = ("istek_izi", "yanit_izi")


def istek_izi_yaz(istek: ReferansIstegi, iz: IstekIzi | None) -> None:
    if iz is not None:
        istek.yanit_isareti = {**(istek.yanit_isareti or {}), "istek_izi": iz.sozluk()}


def form_acildi(referans: ReferansIstegi, simdi: dt.datetime) -> bool:
    """İlk açılış anını yazar (bekleyen istekte, bir kez). Yazdıysa True (commit gerekir)."""
    isaret = referans.yanit_isareti or {}
    if referans.durum != DURUM_BEKLIYOR or "form_acilis" in isaret:
        return False
    referans.yanit_isareti = {**isaret, "form_acilis": simdi.isoformat()}
    return True


def _gencin_istekleri(kullanici_id: uuid.UUID):
    return (
        select(ReferansIstegi.yanit_isareti)
        .join(SomutCikti, SomutCikti.id == ReferansIstegi.somut_cikti_id)
        .join(YetenekKarti, YetenekKarti.id == SomutCikti.yetenek_karti_id)
        .where(YetenekKarti.kullanici_id == kullanici_id)
    )


def _yanitlayan_genc_sayisi(kosul):
    return (
        select(func.count(func.distinct(YetenekKarti.kullanici_id)))
        .select_from(ReferansIstegi)
        .join(SomutCikti, SomutCikti.id == ReferansIstegi.somut_cikti_id)
        .join(YetenekKarti, YetenekKarti.id == SomutCikti.yetenek_karti_id)
        .where(ReferansIstegi.durum == DURUM_YANITLANDI, kosul)
    )


async def yanit_sinyalleri(
    oturum: AsyncSession,
    referans: ReferansIstegi,
    cikti: SomutCikti,
    yanit_izi: IstekIzi | None,
    simdi: dt.datetime,
) -> tuple[str, ...]:
    """Yanıt kaydedildikten sonra (durum `yanitlandi`): izi yazar, sinyal varsa işaret açar."""
    kullanici_id = await oturum.scalar(
        select(YetenekKarti.kullanici_id).where(YetenekKarti.id == cikti.yetenek_karti_id)
    )
    isaret: dict[str, Any] = dict(referans.yanit_isareti or {})
    iz = yanit_izi or IstekIzi(None, None)

    istekler = await oturum.scalars(_gencin_istekleri(kullanici_id))
    genc_izleri = [(a or {}).get("istek_izi") or {} for a in istekler]
    genc_sayisi = await oturum.scalar(
        _yanitlayan_genc_sayisi(
            func.lower(ReferansIstegi.referans_email) == referans.referans_email.strip().lower()
        )
    )
    if iz.ip:
        ayni_ip = ReferansIstegi.yanit_isareti["yanit_izi"]["ip"].astext == iz.ip
        ip_sayisi = await oturum.scalar(
            _yanitlayan_genc_sayisi(ayni_ip | (ReferansIstegi.id == referans.id))
        )
        genc_sayisi = max(genc_sayisi, ip_sayisi)

    acilis = isaret.get("form_acilis")
    sure = (simdi - dt.datetime.fromisoformat(acilis)).total_seconds() if acilis else None
    sinyaller = referans_sinyalleri(
        yanit_ip=iz.ip,
        yanit_tarayici=iz.tarayici,
        genc_ipleri={i["ip"] for i in genc_izleri if i.get("ip")},
        genc_tarayicilari={i["tarayici"] for i in genc_izleri if i.get("tarayici")},
        form_acildi=acilis is not None,
        form_suresi_sn=sure,
        genc_sayisi=genc_sayisi,
    )
    referans.yanit_isareti = {
        **isaret,
        "yanit_izi": iz.sozluk(),
        "form_suresi_sn": round(sure) if sure is not None else None,
        "sinyaller": list(sinyaller),
    }
    if sinyaller:
        await inceleme.sinyal_ekle(
            oturum,
            TUR_REFERANS_SUPHELI,
            kullanici_id,
            cikti.id,
            "referanslar",
            [
                {
                    "anahtar": str(referans.id),
                    "referans_id": str(referans.id),
                    "sinyaller": list(sinyaller),
                    "form_suresi_sn": round(sure) if sure is not None else None,
                    "genc_sayisi": genc_sayisi,
                }
            ],
        )
    return sinyaller


async def eski_izleri_temizle(oturum: AsyncSession, simdi: dt.datetime) -> int:
    """90 günü geçen isteklerden IP ve tarayıcı özetlerini siler (sinyaller kalır)."""
    eskiler = await oturum.scalars(
        select(ReferansIstegi).where(
            ReferansIstegi.olusturma_tarihi < iz_saklama_siniri(simdi),
            ReferansIstegi.yanit_isareti.has_any(array(IZ_ALANLARI)),
        )
    )
    sayi = 0
    for referans in eskiler:
        referans.yanit_isareti = {
            k: v for k, v in (referans.yanit_isareti or {}).items() if k not in IZ_ALANLARI
        }
        sayi += 1
    return sayi
