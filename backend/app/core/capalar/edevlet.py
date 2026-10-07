"""e-Devlet barkodlu belgenin tanınması (docs/dogrulama.md § 4.2). Saf.

e-Devlet'in doğrulama sayfası barkod ve T.C. kimlik no ister; sunucudan
doğrulanamaz. Belge tanınır, barkod numarası ayıklanır ve GİRVAK'a elle
doğrulama için iletilir (`edevlet_barkodu` işareti). T.C. kimlik no saklanmaz:
metin zaten maskelenmiştir, GİRVAK numarayı belgenin kendisinden okur.
"""

from __future__ import annotations

import re

from app.core.metin import turkce_kucult

_EDEVLET = re.compile(r"e-?devlet|turkiye\.gov\.tr|türkiye\.gov\.tr")
# Anahtar kelime harf büyüklüğünden bağımsız; barkodun kendisi büyük harf ve rakam,
# parçalar yalnızca "-" ya da "." ile ayrılır (arkasındaki cümle barkoda karışmasın).
_BARKOD = re.compile(
    r"(?i:barkod(?:\s*(?:no|numarası|numarasi))?)\s*[:：]?\s*"
    r"([A-Z0-9]{2,}(?:[-.][A-Z0-9]{2,}){0,6})\b"
)
EN_AZ_BARKOD = 8


def edevlet_barkodu(metin: str | None) -> str | None:
    """Belge e-Devlet belgesiyse barkod numarası; değilse None."""
    if not metin or not _EDEVLET.search(turkce_kucult(metin)):
        return None
    for eslesme in _BARKOD.finditer(metin):
        barkod = eslesme.group(1)
        if len(re.sub(r"[-.]", "", barkod)) >= EN_AZ_BARKOD and any(c.isdigit() for c in barkod):
            return barkod
    return None
