"""İtiraz: genç değerlendirmeyi eksik bulursa yeniden baktırır (plan § 11.4).

Not zorunlu ve beyandır: kanıt yerine geçmez, tek başına destek sayılmaz. Aynı
not ve aynı girdi önceki sonucu döndürür (önbellek, model çağrılmaz); içerik
sürümü başına en çok `ITIRAZ_SINIRI` itiraz yapılır. Çalışma ya da kanıt
değişince sayaç sıfırlanır (parcalar.py, kart düzenleme). Üçüncü taraf onayı
korunur. Yeni kanıt itirazla değil, kanıt bölümünden parça olarak eklenir.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dogrulama.kurallar import OkunanKanit
from app.models.somut_cikti import SomutCikti
from app.servisler.dogrulama.kanit import hazirla, onbellekte_mi, uygula

# Sonrası GİRVAK inceleme kuyruğu (adım 6); o zamana kadar 429.
ITIRAZ_SINIRI = 3


class ItirazSiniri(Exception):
    """Bu içerik sürümünde itiraz hakkı doldu. Mesaj kullanıcıya gösterilir."""


async def itiraz_et(oturum: AsyncSession, cikti: SomutCikti, aciklama: str) -> OkunanKanit | None:
    hazirlik = await hazirla(oturum, cikti, itiraz_notu=aciklama)
    # Önbellekten dönen (aynı not, aynı girdi) itiraz model çağırmaz, hak harcamaz:
    # sınıra takılmamalı.
    if onbellekte_mi(cikti, hazirlik):
        return hazirlik.okunan
    sayi = cikti.guven_skoru.itiraz_sayisi if cikti.guven_skoru is not None else 0
    if sayi >= ITIRAZ_SINIRI:
        raise ItirazSiniri(
            "Bu çalışma için itiraz hakkını kullandın. Çalışmanı ya da kanıtını "
            "değiştirirsen yeniden değerlendirilir."
        )
    await uygula(oturum, cikti, hazirlik)
    cikti.guven_skoru.itiraz_sayisi = sayi + 1
    return hazirlik.okunan
