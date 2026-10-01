"""İtiraz: genç değerlendirmeyi eksik bulursa yeniden baktırır (plan § 11.4).

Not zorunlu ve beyandır: kanıt yerine geçmez, tek başına destek sayılmaz. Aynı
not ve aynı girdi önceki sonucu döndürür (önbellek, model çağrılmaz); içerik
sürümü başına en çok `ITIRAZ_SINIRI` itiraz yapılır; sonrakiler model çağırmaz,
GİRVAK inceleme kuyruğuna `itiraz_siniri` işaretiyle gider (kalem başına tek
açık işaret, notlar birikir; plan § 9). Çalışma ya da kanıt değişince sayaç
sıfırlanır (parcalar.py, kart düzenleme). Üçüncü taraf onayı
korunur. Yeni kanıt itirazla değil, kanıt bölümünden parça olarak eklenir.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dogrulama.kurallar import OkunanKanit
from app.models.inceleme_isareti import TUR_ITIRAZ_SINIRI
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler import inceleme
from app.servisler.dogrulama.kanit import hazirla, onbellekte_mi, uygula

# Sonrası GİRVAK inceleme kuyruğu.
ITIRAZ_SINIRI = 3


class ItirazIncelemede(Exception):
    """Hak doldu, itiraz GİRVAK'a iletildi. Mesaj kullanıcıya gösterilir."""


def _notlari_birlestir(eski: dict[str, Any], yeni: dict[str, Any]) -> dict[str, Any]:
    return {**eski, "itiraz_notlari": [*eski.get("itiraz_notlari", []), *yeni["itiraz_notlari"]]}


async def itiraz_et(oturum: AsyncSession, cikti: SomutCikti, aciklama: str) -> OkunanKanit | None:
    hazirlik = await hazirla(oturum, cikti, itiraz_notu=aciklama)
    # Önbellekten dönen (aynı not, aynı girdi) itiraz model çağırmaz, hak harcamaz:
    # sınıra takılmamalı.
    if onbellekte_mi(cikti, hazirlik):
        return hazirlik.okunan
    sayi = cikti.guven_skoru.itiraz_sayisi if cikti.guven_skoru is not None else 0
    if sayi >= ITIRAZ_SINIRI:
        kart = await oturum.get(YetenekKarti, cikti.yetenek_karti_id)
        await inceleme.isaret_ac(
            oturum,
            TUR_ITIRAZ_SINIRI,
            kart.kullanici_id,
            somut_cikti_id=cikti.id,
            ayrinti={"itiraz_notlari": [aciklama]},
            birlestir=_notlari_birlestir,
        )
        raise ItirazIncelemede(
            "İtirazın GİRVAK'a iletildi; inceleyip sonucu sana bildirecek. Çalışmanı "
            "ya da kanıtını değiştirirsen yeniden değerlendirilir."
        )
    await uygula(oturum, cikti, hazirlik)
    cikti.guven_skoru.itiraz_sayisi = sayi + 1
    return hazirlik.okunan
