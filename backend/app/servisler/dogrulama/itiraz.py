"""İtiraz: genç değerlendirmeyi eksik bulursa rubrik yeniden hesaplanır.

Skor kaydı silinmez, üzerine yazılır. Üçüncü taraf onayı korunur: referans
zaten yanıtlamışsa itiraz onu geçersiz kılmamalı. İtiraz notu rubriğe gencin
BEYANI olarak girer, kanıt yerine geçmez (kuralı istemde yazılı).

İtiraz link değiştirmez: yeni kanıt kanıt bölümünden parça olarak eklenir
(tek kapı, bulgu 25).
"""

from __future__ import annotations

from app.agents.dogrulama import LinkKontrolu
from app.models.somut_cikti import SomutCikti
from app.servisler.dogrulama.kanit import degerlendir


async def itiraz_et(cikti: SomutCikti, *, aciklama: str | None) -> LinkKontrolu:
    return await degerlendir(cikti, itiraz_notu=aciklama)
