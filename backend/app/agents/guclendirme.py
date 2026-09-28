"""'Kartını güçlendir': kanıt eklemenin fırsatlardaki etkisi (docs/plans/genc-akisi.md § 7).

Saf hesap, yapay zekâ yok. Sayılar gerçek skorlardan gelir; metin şablondur ve
Canlılık'taki kuralla denetlenir: metinde girdide olmayan sayı geçemez.

Varsayım (en iyi durum, açıkça söylenir: "öne çıkabilirsin"): kanıtı eksik
çalışmaya işin kendisine götüren bir kanıt eklenir (kanıt orijinalliği 3/3),
diğer bileşenler olduğu gibi kalır. Kartın doğrulama bonusu yeniden hesaplanır;
skor = 0.75·benzerlik + 0.25·bonus olduğundan benzerlik değişmez, fark yalnızca
0.25·(yeni bonus − eski bonus). Her fırsatta (gencin görebildiği `onerildi`
öneri) kartın o ihtiyacın adayları arasındaki sırası yükseliyorsa sayılır.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.agents.canlilik import kisisel_metin_gecerli_mi
from app.agents.eslestirme import DOGRULAMA_AGIRLIGI, dogrulama_bonusu

# Bir çalışmanın güven göstergesi: (kanıt, sonuç, rol, referans), yoksa None.
Gosterge = tuple[int, int, int, int] | None

TAM_KANIT = 3


@dataclass(frozen=True)
class FirsatSirasi:
    """Bir fırsatta kartın skoru ve aynı ihtiyacın diğer adaylarının skorları."""

    kendi_skoru: float
    rakip_skorlari: Sequence[float]


def kanitli_gosterge(gosterge: Gosterge) -> tuple[int, int, int, int]:
    """Varsayım: kanıt 3/3 olur, diğer bileşenler aynı kalır (yoksa 0)."""
    _, sonuc, rol, referans = gosterge or (0, 0, 0, 0)
    return (TAM_KANIT, sonuc, rol, referans)


def bonus_farki(
    gostergeler: Mapping[object, Gosterge], cikti_id: object, tamamlanan_pilot: int
) -> float:
    """O çalışmaya tam kanıt eklenirse skor ne kadar artar (0 ile 0.25 arası)."""
    once = [g for g in gostergeler.values() if g is not None]
    sonra = [
        kanitli_gosterge(g) if kimlik == cikti_id else g
        for kimlik, g in gostergeler.items()
        if kimlik == cikti_id or g is not None
    ]
    eski = dogrulama_bonusu(once, tamamlanan_pilot)
    yeni = dogrulama_bonusu(sonra, tamamlanan_pilot)
    return DOGRULAMA_AGIRLIGI * max(0.0, yeni - eski)


def sira(skor: float, rakipler: Sequence[float]) -> int:
    """1'den başlayan sıra: kendisinden yüksek skorlu rakip sayısı + 1."""
    return 1 + sum(r > skor for r in rakipler)


def one_cikacagi_firsat_sayisi(siralar: Sequence[FirsatSirasi], fark: float) -> int:
    """Skor `fark` kadar artarsa kaç fırsatta sıra yükselir?"""
    if fark <= 0:
        return 0
    return sum(
        sira(s.kendi_skoru + fark, s.rakip_skorlari) < sira(s.kendi_skoru, s.rakip_skorlari)
        for s in siralar
    )


def guclendirme_metni(sayi: int) -> str:
    """Rehbere göre ("çalışma", "fırsat", sen); sayı girdiden gelir, denetlenir."""
    if sayi > 0:
        metin = f"Bu çalışmaya kanıt eklersen {sayi} fırsatta öne çıkabilirsin."
    else:
        metin = "Kanıt eklemek, yeni fırsatlarda kartını güçlendirir."
    # Canlılık'taki kural: girdide olmayan sayı metne giremez.
    if not kisisel_metin_gecerli_mi(metin, str(sayi)):
        return "Kanıt eklemek, yeni fırsatlarda kartını güçlendirir."
    return metin
