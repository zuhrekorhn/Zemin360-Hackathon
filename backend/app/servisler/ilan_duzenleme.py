"""İlan (ihtiyaç kartı) yerinde düzenleme (docs/kararlar.md D1).

Kural app/agents/ihtiyac_duzenleme.py; burada kuralın sonucunu uygulayan iş:
alanları yazmak, eski gerekçeleri sıfırlamak, ilgilenmiş aday tarafına nötr
bildirim. Kilit, commit, embedding ve yeniden eşleştirme uçta
(app/api/ihtiyac_kartlari.py › ihtiyac_karti_duzenle).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.ihtiyac_duzenleme import (
    bildirim_alacak,
    degisen_alanlar,
    duzenlenebilir_mi,
    gerekcesi_sifirlanacak,
)
from app.core import calisma_modeli
from app.core.firma_karti import ISBIRLIGI_TURLERI
from app.core.firma_profili import firma_turlerini_temizle
from app.core.ilan import ARANAN_FIRMA
from app.core.sehir import sehir_kanonik
from app.models.bildirim import TUR_FIRSAT_GUNCELLENDI
from app.models.eslesme import Eslesme
from app.models.ihtiyac_karti import IhtiyacKarti
from app.schemas.tanimlama import IhtiyacTaslagi
from app.servisler.bildirim import bildirim_ekle
from app.servisler.eslestirme import iliskileriyle
from app.servisler.sahiplik import TARAF_ADAY, taraf_hesabi

FIRSAT_GUNCELLENDI = "İlgilendiğin bir fırsatın ayrıntıları güncellendi."
FIRSAT_GUNCELLENDI_SIZ = "İlgilendiğiniz bir fırsatın ayrıntıları güncellendi."


def taslak_alanlari(taslak: IhtiyacTaslagi, ortak: bool) -> dict[str, Any]:
    """Taslağın kartta saklanan hali. Onay ve düzenleme aynı yoldan yazar.

    Çalışma modeli ve müsaitlik genç ilanına, firma türleri ve iş birliği türü
    ortak ilanına özel; öbür ilanda boş yazılır.
    """
    return {
        "problem_tanimi": taslak.problem_tanimi,
        "basari_kriteri": taslak.basari_kriteri,
        "basari_olcutu": taslak.basari_olcutu.model_dump() if taslak.basari_olcutu else None,
        "kisitlar": taslak.kisitlar,
        "sehir_tercihi": sehir_kanonik(taslak.sehir_tercihi),
        "calisma_modeli": (
            taslak.calisma_modeli
            if not ortak and calisma_modeli.gecerli_mi(taslak.calisma_modeli)
            else None
        ),
        "musaitlik_tercihi": None if ortak else taslak.musaitlik_tercihi,
        "aranan_firma_turleri": (
            firma_turlerini_temizle(taslak.aranan_firma_turleri) if ortak else []
        ),
        "isbirligi_turu": (
            taslak.isbirligi_turu if ortak and taslak.isbirligi_turu in ISBIRLIGI_TURLERI else None
        ),
    }


async def ilan_eslesmeleri(oturum: AsyncSession, ilan: IhtiyacKarti) -> list[Eslesme]:
    """İlanın eşleşmeleri, taraflarıyla ve kilitli (pipeline ile yarışmasın)."""
    return list(
        await oturum.scalars(
            iliskileriyle(select(Eslesme))
            .where(Eslesme.ihtiyac_karti_id == ilan.id)
            .with_for_update(of=Eslesme)
        )
    )


def duzenleme_engeli(ilan: IhtiyacKarti, eslesmeler: list[Eslesme]) -> str | None:
    return duzenlenebilir_mi(ilan.durum, (e.durum for e in eslesmeler))


def ilani_duzenle(
    oturum: AsyncSession,
    ilan: IhtiyacKarti,
    eslesmeler: list[Eslesme],
    taslak: IhtiyacTaslagi,
) -> bool:
    """Alanları yazar; değiştiyse gerekçeleri sıfırlar ve bildirir. Döner: değişti mi.

    Değişmeyen düzenleme hiçbir şeye dokunmaz. Commit çağıranın işi.
    """
    yeni = taslak_alanlari(taslak, ilan.aranan == ARANAN_FIRMA)
    eski = {alan: getattr(ilan, alan) for alan in yeni}
    if not degisen_alanlar(eski, yeni):
        return False
    for alan, deger in yeni.items():
        setattr(ilan, alan, deger)
    for eslesme in eslesmeler:
        if gerekcesi_sifirlanacak(eslesme.durum):
            eslesme.gerekce_metni = eslesme.aday_gerekce_metni = None
            # Karar gerekçeye dayanır: birlikte sıfırlanır, sonraki hesapta yeniden yargılanır.
            eslesme.uygunluk = None
        if bildirim_alacak(eslesme.durum):
            bildirim_ekle(
                oturum,
                taraf_hesabi(eslesme, TARAF_ADAY),
                TUR_FIRSAT_GUNCELLENDI,
                FIRSAT_GUNCELLENDI_SIZ if eslesme.firma_karti is not None else FIRSAT_GUNCELLENDI,
                eslesme.id,
            )
    return True
