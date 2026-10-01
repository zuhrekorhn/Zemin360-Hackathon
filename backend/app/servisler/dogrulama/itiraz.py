"""İtiraz: genç değerlendirmeyi eksik bulursa rubrik yeniden hesaplanır.

Skor kaydı silinmez, üzerine yazılır. Üçüncü taraf onayı korunur: referans
zaten yanıtlamışsa itiraz onu geçersiz kılmamalı. İtiraz notu rubriğe gencin
BEYANI olarak girer, kanıt yerine geçmez (kuralı istemde yazılı).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dogrulama import LinkKontrolu, linki_kontrol_et
from app.models.somut_cikti import SomutCikti
from app.servisler.dogrulama.kanit import kanit_bekleyeni_guncelle, rubrigi_yaz


async def itiraz_et(
    oturum: AsyncSession,
    cikti: SomutCikti,
    *,
    yeni_kanit_linki: str | None,
    aciklama: str | None,
) -> LinkKontrolu:
    if yeni_kanit_linki:
        cikti.kanit_linki = yeni_kanit_linki

    kontrol = await linki_kontrol_et(cikti.kanit_linki)
    await rubrigi_yaz(cikti, kontrol, itiraz_notu=aciklama)
    await kanit_bekleyeni_guncelle(oturum, cikti.yetenek_karti_id)
    return kontrol
