"""Alıntı denetimi: modelin "kanıtta şu yazıyor" dediği parça gerçekten metinde mi?

RAG'deki dayanaklılık (grounding) deseni (docs/dogrulama.md § 11.1): model iddiayı destekleyen
yeri birebir alıntılar, kod alıntıyı tam metinde arar. Geçmeyen destek yok
sayılır; böylece uydurma ve kanıt metnine gömülmüş talimatlar (istem
enjeksiyonu) puana yansımaz.

Model alıntıyı küçük farklarla verebilir (büyük/küçük harf, boşluk,
noktalama, tırnak), bu yüzden birebir değil normalleştirilmiş kısmi benzerlik
aranır. Yeni bağımlılık yerine standart kütüphanenin `difflib`'i: kısa
alıntılarda yeterli.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.core.metin import turkce_kucult

ESIK = 0.9
# Çok kısa alıntı ("evet", "3") her metinde bulunur; destek sayılmaz.
EN_KISA_ALINTI = 8


def normallestir(metin: str) -> str:
    """Türkçe küçük harf, noktalama yerine boşluk, tek boşluk."""
    return " ".join(re.sub(r"[^\w\s]", " ", turkce_kucult(metin)).split())


def benzerlik(alinti: str, metin: str) -> float:
    """Alıntının metindeki en iyi eşleşen penceresiyle oranı (0-1)."""
    a, m = normallestir(alinti), normallestir(metin)
    if not a or not m:
        return 0.0
    if a in m:
        return 1.0
    eslestirici = SequenceMatcher(None, m, a, autojunk=False)
    en_iyi = 0.0
    for blok in eslestirici.get_matching_blocks():
        bas = max(0, blok.a - blok.b)
        pencere = m[bas : bas + len(a)]
        en_iyi = max(en_iyi, SequenceMatcher(None, pencere, a, autojunk=False).ratio())
    return en_iyi


def alinti_gecerli_mi(alinti: str | None, metin: str) -> bool:
    return (
        bool(alinti)
        and len(normallestir(alinti)) >= EN_KISA_ALINTI
        and benzerlik(alinti, metin) >= ESIK
    )
