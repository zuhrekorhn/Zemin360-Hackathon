"""Takip testlerinin ortak dünyası (test_sahiplik.py'dekinin üstüne).

E1 (kurum1 "Koop Bir" ↔ genc1 "Elif") kabul edilmiş, iş birliği `plan_bekliyor`,
planı boş: genç kabul ettikten hemen sonraki an.

    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d)
    senaryo(adimlar)
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select

from app.agents import takip
from app.agents.takip_durumu import ISBIRLIGI_PLAN_BEKLIYOR, MILESTONE_BEKLIYOR
from app.models.bildirim import Bildirim
from app.models.isbirligi import Isbirligi
from app.models.milestone import Milestone

BASLANGIC = dt.date(2026, 9, 29)

ORNEK_PLAN = [
    takip.AdimOnerisi(baslik="Mevcut kayıtları incele", aciklama="Defterler tarandı.", hafta=1),
    takip.AdimOnerisi(baslik="Kayıt ekranı", aciklama="10 kayıt hatasız girildi.", hafta=3),
    takip.AdimOnerisi(baslik="Aylık rapor", aciklama="Rapor 10 dakikada çıktı.", hafta=6),
]


async def isbirligi_ac(d, *, adimlar: int = 0) -> Isbirligi:
    """E1'i kabul edilmiş yapar ve iş birliği açar; istenirse `adimlar` kadar adım ekler."""
    d.E1.durum = "kabul_edildi"
    isbirligi = Isbirligi(
        eslesme_id=d.E1.id, baslangic_tarihi=BASLANGIC, durum=ISBIRLIGI_PLAN_BEKLIYOR
    )
    for sira in range(adimlar):
        isbirligi.milestonelar.append(
            Milestone(
                baslik=f"Adım {sira + 1}",
                sira=sira,
                hedef_tarih=BASLANGIC + dt.timedelta(weeks=sira + 1),
                durum=MILESTONE_BEKLIYOR,
            )
        )
    d.oturum.add(isbirligi)
    await d.oturum.commit()
    return isbirligi


async def bildirimleri(d, kisi) -> list[Bildirim]:
    return list(
        await d.oturum.scalars(
            select(Bildirim)
            .where(Bildirim.hesap_id == kisi.hesap.id)
            .order_by(Bildirim.olusturma_tarihi)
        )
    )


def sahte_plan(monkeypatch, sonuc=ORNEK_PLAN) -> list:
    """Ajanın plan çağrısını sahtesiyle değiştirir; çağrıları sayar."""
    cagrilar: list = []

    async def oner(ihtiyac, kart, kurum_adi):
        cagrilar.append((ihtiyac.id, kart.id, kurum_adi))
        return sonuc

    monkeypatch.setattr(takip, "plan_oner", oner)
    return cagrilar
