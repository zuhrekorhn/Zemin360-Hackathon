"""PDF'in metin katmanı (docs/dogrulama.md § 4.3). Metin katmanı yoksa ya da sayfa başına çok azsa
(taranmış belge, görsel ağırlıklı portfolyo) PDF modele okutulur; o karar burada.
"""

from __future__ import annotations

import io
import logging

logger = logging.getLogger("zemin360.pdf")

# Sayfa başına bundan az karakter: belge görsel ağırlıklı sayılır, model de okur.
SAYFA_BASINA_ASGARI = 80
# Modele okunacak / saklanacak en çok sayfa (Gemini sınırı 1000; maliyet için düşük)
AZAMI_SAYFA = 50


def pdf_metni(veri: bytes) -> tuple[str, int]:
    """(metin, sayfa sayısı). Okunamazsa boş metin; yükleme hattı PDF'i zaten açabildi."""
    from pypdf import PdfReader

    try:
        okuyucu = PdfReader(io.BytesIO(veri))
        sayfalar = okuyucu.pages[:AZAMI_SAYFA]
        metin = "\n\n".join((s.extract_text() or "").strip() for s in sayfalar)
        return metin.strip(), len(okuyucu.pages)
    except Exception:
        logger.warning("pdf metni cikarilamadi", exc_info=True)
        return "", 0


def model_okumali_mi(metin: str, sayfa_sayisi: int) -> bool:
    return len(metin) < SAYFA_BASINA_ASGARI * max(1, min(sayfa_sayisi, AZAMI_SAYFA))
