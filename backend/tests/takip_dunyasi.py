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

# E1'in ilanında müsaitlik yok: işe alım süreci. Model iki adımı kişiselleştirir,
# biri tanınmayan anahtar (yok sayılır); diğer adımlar şablon metniyle kalır.
ORNEK_PLAN = takip.KisiselPlan(
    adimlar=[
        takip.KisiselAdim(
            anahtar="gorusme_yapildi",
            tamam_tanimi="Ödünç süreci örnek bir gün üzerinden konuşuldu.",
            oneri="Kütüphane sistemi çalışmasını anlatmasını isteyin.",
        ),
        takip.KisiselAdim(
            anahtar="deneme_gorevi",
            tamam_tanimi="Kayıt ekranının taslağı teslim edildi.",
            oneri="Görevi tek bir ödünç kaydı ekranıyla sınırlayın.",
        ),
        takip.KisiselAdim(anahtar="uydurma_adim", tamam_tanimi="x", oneri="y"),
    ]
)


class SahteZincir:
    """Modelin yerine: sonucu döner ya da istisnaysa fırlatır; girdileri kaydeder."""

    def __init__(self, sonuc, cagrilar: list) -> None:
        self.sonuc = sonuc
        self.cagrilar = cagrilar

    async def ainvoke(self, girdiler):
        self.cagrilar.append(girdiler)
        if isinstance(self.sonuc, BaseException):
            raise self.sonuc
        return self.sonuc


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
    """Modelin kişiselleştirme çağrısını sahtesiyle değiştirir; istem girdilerini kaydeder.

    `sonuc` bir istisnaysa çağrı onu fırlatır (şablona düşme yolu gerçekten çalışır).
    """
    cagrilar: list = []
    monkeypatch.setattr(takip, "_plan_zinciri", lambda: SahteZincir(sonuc, cagrilar))
    return cagrilar
