"""Doğrulama rubriğinin yazılması: kanıt ekleme, itiraz ve kart hazırlama aynı yoldan.

Kural ve LLM app/agents/dogrulama.py'de; burada rubriğin iş kalemine yazılması.
Hata çevirisi (hız sınırı → 429) uçların işi: arka plan işi aynı hatayı yakalayıp
kalemi puansız bırakır.
"""

from __future__ import annotations

from app.agents.dogrulama import (
    LinkKontrolu,
    ReferansYaniti,
    gecerli_referans_puanlari,
    linki_kontrol_et,
    referans_gecerli_mi,
    rubrik_puanla,
    ucuncu_taraf_onayi_hesapla,
)
from app.core.is_kalemi import is_kalemi_metni
from app.models.guven_skoru import GuvenSkoru
from app.models.somut_cikti import SomutCikti


def referans_guncel_mi(cikti: SomutCikti, referans) -> bool:
    """Bu referans yanıtı iş kaleminin güncel hâli için mi? (plan § 0, karar 8)"""
    return referans_gecerli_mi(
        getattr(referans, "yanit_tarihi", None), getattr(cikti, "icerik_tarihi", None)
    )


def ucuncu_taraf_puani(cikti: SomutCikti) -> int:
    """Yalnızca güncel referans yanıtlarından; iş değiştiyse eski yanıtlar girmez.

    `cikti.referans_istekleri` yüklenmiş olmalı.
    """
    return ucuncu_taraf_onayi_hesapla(
        gecerli_referans_puanlari(
            [
                ReferansYaniti(puan=r.puan, yanit_tarihi=getattr(r, "yanit_tarihi", None))
                for r in cikti.referans_istekleri
            ],
            getattr(cikti, "icerik_tarihi", None),
        )
    )


async def rubrigi_yaz(
    cikti: SomutCikti, kontrol: LinkKontrolu, itiraz_notu: str | None = None
) -> None:
    """Ön rubriği üretip kaydeder; üçüncü taraf onayı korunur.

    LLM hataları (hız sınırı, arıza) çağırana çıkar. Commit çağıranın işi.
    """
    puan = await rubrik_puanla(
        baslik=cikti.baslik,
        # Sonuç ve rol ayrı alanlarda; rubrik işi tek metin olarak okur.
        aciklama=is_kalemi_metni(cikti),
        kanit_linki=cikti.kanit_linki,
        kontrol=kontrol,
        itiraz_notu=itiraz_notu,
    )

    if cikti.guven_skoru is None:
        cikti.guven_skoru = GuvenSkoru(
            kanit_orijinalligi=puan.kanit_orijinalligi,
            sonuc_olculebilirligi=puan.sonuc_olculebilirligi,
            rol_netligi=puan.rol_netligi,
            # Sıfırdan yazılıyor (ilk puan ya da iş değiştiği için sıfırlandı):
            # değişiklikten sonra gelmiş referans yanıtı varsa o sayılır.
            ucuncu_taraf_onayi=ucuncu_taraf_puani(cikti),
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
