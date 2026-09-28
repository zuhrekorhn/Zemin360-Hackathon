"""Doğrulama rubriğinin yazılması: kanıt ekleme, itiraz ve kart hazırlama aynı yoldan.

Kural ve LLM app/agents/dogrulama.py'de; burada rubriğin iş kalemine yazılması.
Hata çevirisi (hız sınırı → 429) uçların işi: arka plan işi aynı hatayı yakalayıp
kalemi puansız bırakır.
"""

from __future__ import annotations

from app.agents.dogrulama import LinkKontrolu, linki_kontrol_et, rubrik_puanla
from app.models.guven_skoru import GuvenSkoru
from app.models.somut_cikti import SomutCikti


async def rubrigi_yaz(
    cikti: SomutCikti, kontrol: LinkKontrolu, itiraz_notu: str | None = None
) -> None:
    """Ön rubriği üretip kaydeder; üçüncü taraf onayı korunur.

    LLM hataları (hız sınırı, arıza) çağırana çıkar. Commit çağıranın işi.
    """
    puan = await rubrik_puanla(
        baslik=cikti.baslik,
        aciklama=cikti.aciklama,
        kanit_linki=cikti.kanit_linki,
        kontrol=kontrol,
        itiraz_notu=itiraz_notu,
    )

    if cikti.guven_skoru is None:
        cikti.guven_skoru = GuvenSkoru(
            kanit_orijinalligi=puan.kanit_orijinalligi,
            sonuc_olculebilirligi=puan.sonuc_olculebilirligi,
            rol_netligi=puan.rol_netligi,
            ucuncu_taraf_onayi=0,  # referans gelene kadar 0
            gerekce_metni=puan.gerekce_metni,
        )
    else:
        cikti.guven_skoru.kanit_orijinalligi = puan.kanit_orijinalligi
        cikti.guven_skoru.sonuc_olculebilirligi = puan.sonuc_olculebilirligi
        cikti.guven_skoru.rol_netligi = puan.rol_netligi
        cikti.guven_skoru.gerekce_metni = puan.gerekce_metni


async def ciktiyi_puanla(cikti: SomutCikti) -> LinkKontrolu:
    """Linki sınar ve rubriği yazar (kart hazırlamanın kalem başına işi)."""
    kontrol = await linki_kontrol_et(cikti.kanit_linki)
    await rubrigi_yaz(cikti, kontrol)
    return kontrol
