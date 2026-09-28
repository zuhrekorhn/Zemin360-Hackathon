"""İş kalemi (somut çıktı): türleri ve rubriğe/embedding'e giden birleşik metin.

Keşif sonucu ve kişinin kendi payını ayrı alanlarda topluyor (düzenlenebilsinler
diye; docs/plans/genc-akisi.md § 3.4). Doğrulama rubriği, embedding temsil metni
ve eşleştirme gerekçesi ise işi tek metin olarak okuyor: birleştirme burada,
tek yerde.
"""

from __future__ import annotations

from typing import Literal, Protocol

PROJE = "proje"
STAJ = "staj"
IS = "is"
GONULLULUK = "gonulluluk"
YARISMA = "yarisma"

IS_TURLERI: tuple[str, ...] = (PROJE, STAJ, IS, GONULLULUK, YARISMA)
IsTuru = Literal["proje", "staj", "is", "gonulluluk", "yarisma"]

ETIKETLER: dict[str, str] = {
    PROJE: "Proje",
    STAJ: "Staj",
    IS: "İş",
    GONULLULUK: "Gönüllülük",
    YARISMA: "Yarışma",
}


def is_turu_hosgorulu(deger: object) -> str | None:
    """Tanınan tür kodu ya da None (eski taslak, model uydurması)."""
    return deger if isinstance(deger, str) and deger in IS_TURLERI else None


class IsKalemiMetni(Protocol):
    aciklama: str | None
    olculebilir_sonuc: str | None
    kendi_rolu: str | None


def birlesik_aciklama(
    aciklama: str | None, olculebilir_sonuc: str | None, kendi_rolu: str | None
) -> str | None:
    """Açıklama, sonuç ve rol tek metinde; boşlar atlanır.

    Bu alanlardan önceki satırlarda sonuç ve rol zaten açıklamanın içinde
    (Keşif birleştiriyordu); açıklamada geçen parça ikinci kez eklenmez.
    """
    ana = (aciklama or "").strip()
    parcalar = [ana] if ana else []
    for parca in (olculebilir_sonuc, kendi_rolu):
        metin = (parca or "").strip()
        if metin and metin not in ana:
            parcalar.append(metin)
    return " ".join(parcalar) or None


def is_kalemi_metni(cikti: IsKalemiMetni) -> str | None:
    """Modelden (SomutCikti) ya da taslaktan birleşik metin."""
    return birlesik_aciklama(
        getattr(cikti, "aciklama", None),
        getattr(cikti, "olculebilir_sonuc", None),
        getattr(cikti, "kendi_rolu", None),
    )
