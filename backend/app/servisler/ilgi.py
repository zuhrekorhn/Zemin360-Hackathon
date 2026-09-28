"""İlgi akışının paylaşılan yan etkileri (docs/plans/genc-akisi.md § 4, § 7.1).

Geçiş kuralı app/agents/eslesme_durumu.py › gecis(). Burada kuralın sonucunu
uygulayan, birden fazla yerin paylaştığı işler:
  - iş birliğini açmak (gencin kabulü ve karşılıklı ilgi aynı yol),
  - ihtiyacı kapatmak (karar verilmemiş kayıtlar "kapandı" olur).

Bildirim metinleri docs/icerik-rehberi.md'ye göre: gence "sen", firmaya "siz",
olumsuz durum nötr ("fırsat kapandı"; nedeni yazılmaz).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.eslesme_durumu import (
    OLAY_IHTIYAC_KAPANDI,
    ROL_SISTEM,
    gecis,
)
from app.agents.eslestirme import (
    DURUM_GENC_ILGILENDI,
    DURUM_ILGILENILIYOR,
    DURUM_ONERILDI,
)
from app.agents.takip_durumu import ISBIRLIGI_PLAN_BEKLIYOR
from app.api.bildirimler import bildirim_ekle
from app.models.bildirim import TUR_FIRSAT_KAPANDI
from app.models.eslesme import Eslesme
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.isbirligi import Isbirligi
from app.servisler.eslestirme import iliskileriyle

IHTIYAC_KAPANDI = "kapandi"


def firsat_kapandi_metni(firma_adi: str) -> str:
    """Gence: nötr, nedeni yazılmaz (rehber § 5.7)."""
    return f"{firma_adi} tarafındaki fırsat kapandı."


def isbirligini_ac(eslesme: Eslesme) -> Isbirligi:
    """İş birliği yoksa açar (plan onayı bekler). Plan önerisi çağıranın arka plan işi."""
    if eslesme.isbirligi is None:
        eslesme.isbirligi = Isbirligi(
            baslangic_tarihi=dt.date.today(), durum=ISBIRLIGI_PLAN_BEKLIYOR
        )
    return eslesme.isbirligi


def kapanacak_mi(durum: str) -> bool:
    """İhtiyaç kapanınca bu kayıt kapanır mı? Karar verilmiş kayıt (kabul, red,
    zaten kapalı) olduğu gibi kalır."""
    return durum in (DURUM_ONERILDI, DURUM_GENC_ILGILENDI, DURUM_ILGILENILIYOR)


async def ihtiyaci_kapat(oturum: AsyncSession, ihtiyac: IhtiyacKarti) -> int:
    """İhtiyacı kapatır; bekleyen ilgiler "kapandı" olur. Döner: kapanan kayıt sayısı.

    Kapalı ihtiyaç eşleştirmeye girmez (pipeline ve kart hazırlama açık ihtiyaca
    bakar). Bir ilgisi beklenen genç (kendi gösterdiği ya da firmanın
    gösterdiği) nötr bir bildirim alır; yalnızca önerilmiş olan almaz, çünkü
    orada bir bekleyiş yoktu. Commit çağıranın işi. Firma arayüzündeki
    "kapat" düğmesi firma görevinde (plan § 0, karar 4).
    """
    ihtiyac.durum = IHTIYAC_KAPANDI
    eslesmeler = await oturum.scalars(
        iliskileriyle(select(Eslesme))
        .where(Eslesme.ihtiyac_karti_id == ihtiyac.id)
        .with_for_update(of=Eslesme)
    )
    simdi = dt.datetime.now(dt.UTC)
    kapanan = 0
    for eslesme in eslesmeler.all():
        if not kapanacak_mi(eslesme.durum):
            continue
        bekleyen_vardi = eslesme.durum != DURUM_ONERILDI
        eslesme.durum = gecis(eslesme.durum, OLAY_IHTIYAC_KAPANDI, ROL_SISTEM).durum
        eslesme.son_aktivite_tarihi = simdi
        kapanan += 1
        if bekleyen_vardi:
            bildirim_ekle(
                oturum,
                eslesme.yetenek_karti.kullanici.hesap_id,
                TUR_FIRSAT_KAPANDI,
                firsat_kapandi_metni(eslesme.ihtiyac_karti.kurum.ad),
                eslesme.id,
            )
    return kapanan
