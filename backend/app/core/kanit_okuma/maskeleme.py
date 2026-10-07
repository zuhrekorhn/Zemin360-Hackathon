"""Dosyadan çıkarılan metinde kişisel verilerin maskelenmesi (docs/dogrulama.md § 4.4, KVKK).

Saklanan metin (`kanit_parcasi.tam_metin`, `gorsel_metni`) maskelenmiştir:
T.C. kimlik numarası (sağlama haneleriyle doğrulanmış 11 hane), telefon ve
açık adres kalıpları. Adres tanıma kalıba dayanır (mahalle / cadde / sokak +
numara); her adresi yakalamaz, bu bilinen bir sınırdır (docs/dogrulama.md § 18).
Saf fonksiyon.
"""

from __future__ import annotations

import re

TC_MASKESI = "[T.C. kimlik no]"
TELEFON_MASKESI = "[telefon]"
ADRES_MASKESI = "[adres]"

_TC = re.compile(r"(?<!\d)([1-9]\d{10})(?!\d)")
# +90 / 0 ile başlayan 10 haneli Türkiye numaraları (boşluk, tire, nokta, parantezli)
_TELEFON = re.compile(
    r"(?<![\w+])(?:\+90|0090|0)?[\s.-]?\(?5\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}(?!\d)"
)
_ADRES = re.compile(
    r"[\wÇĞİÖŞÜçğıöşü.]+\s+(?:Mahallesi|Mah\.|Mh\.)"
    r"[^\n]{0,80}?(?:No|Numara)\s*[:.]?\s*\d+[\w/]*(?:\s*(?:D|Daire)\s*[:.]?\s*\d+)?",
    re.IGNORECASE,
)


def tc_kimlik_gecerli_mi(no: str) -> bool:
    if len(no) != 11 or not no.isdigit() or no[0] == "0":
        return False
    h = [int(c) for c in no]
    onuncu = ((sum(h[0:9:2]) * 7) - sum(h[1:8:2])) % 10
    return h[9] == onuncu and h[10] == sum(h[:10]) % 10


def maskele(metin: str) -> str:
    metin = _ADRES.sub(ADRES_MASKESI, metin)
    metin = _TC.sub(lambda m: TC_MASKESI if tc_kimlik_gecerli_mi(m.group(1)) else m.group(0), metin)
    return _TELEFON.sub(TELEFON_MASKESI, metin)
