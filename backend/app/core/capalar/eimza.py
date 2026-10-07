"""PDF'teki elektronik imzaların (PAdES) okunması (docs/dogrulama.md § 4.2; `pyHanko`).

Ham dosyadan çalışır: temizlik PDF'i yeniden yazdığı için imzanın bayt aralığını
bozar. Doğrulama yereldir: iptal listesi / OCSP için ağ isteği atılmaz
(`allow_fetching=False`; sunucudan kullanıcı adresine istek yok, süre öngörülebilir),
iptal denetimi "soft-fail". Güvenilir kökler: certifi (Mozilla) + isteğe bağlı
yerel klasör (`EIMZA_KOK_KLASORU`, ör. Kamu SM kökleri; .pem / .crt / .cer).

Kaydedilen gerçekler: imza matematiksel olarak geçerli mi (`gecerli`), belge
imzadan sonra değişmiş mi (`butun`), zincir güvenilir köke gidiyor mu
(`guvenilir`), imzalayanın adı. Seviyeye karar vermez.
"""

from __future__ import annotations

import io
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger("zemin360.eimza")

AZAMI_IMZA = 5


def _pem_sertifikalari(veri: bytes) -> list[Any]:
    from asn1crypto import pem, x509

    if pem.detect(veri):
        return [x509.Certificate.load(der) for _, _, der in pem.unarmor(veri, multiple=True)]
    return [x509.Certificate.load(veri)]


@lru_cache
def guvenilir_kokler(klasor: str = "") -> tuple[Any, ...]:
    import certifi

    kokler = _pem_sertifikalari(Path(certifi.where()).read_bytes())
    if klasor:
        for yol in Path(klasor).glob("*"):
            if yol.suffix.lower() in (".pem", ".crt", ".cer"):
                try:
                    kokler.extend(_pem_sertifikalari(yol.read_bytes()))
                except Exception:
                    logger.warning("kok sertifika okunamadi: %s", yol.name)
    return tuple(kokler)


def imzalari_oku(ham: bytes, kokler: tuple[Any, ...]) -> list[dict[str, Any]]:
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko.sign.validation.status import ModificationLevel, SignatureCoverageLevel
    from pyhanko_certvalidator import ValidationContext

    okuyucu = PdfFileReader(io.BytesIO(ham), strict=False)
    imzalar = []
    for imza in okuyucu.embedded_signatures[:AZAMI_IMZA]:
        baglam = ValidationContext(
            trust_roots=list(kokler), allow_fetching=False, revocation_mode="soft-fail"
        )
        try:
            durum = validate_pdf_signature(imza, baglam)
        except Exception:
            logger.warning("imza dogrulanamadi", exc_info=True)
            imzalar.append({"gecerli": False, "butun": False, "guvenilir": False})
            continue
        kapsam_tam = durum.coverage in (
            SignatureCoverageLevel.ENTIRE_FILE,
            SignatureCoverageLevel.ENTIRE_REVISION,
        )
        degisiklik = durum.modification_level
        imzalar.append(
            {
                "gecerli": bool(durum.intact and durum.valid),
                # Sonraki sürümlerde yalnızca form doldurma / yeni imza olabilir.
                "butun": kapsam_tam
                and (degisiklik is None or degisiklik <= ModificationLevel.FORM_FILLING)
                and durum.docmdp_ok is not False,
                "guvenilir": bool(durum.trusted),
                "imzalayan": durum.signing_cert.subject.human_friendly[:200],
                "imza_tarihi": durum.signer_reported_dt.isoformat()
                if durum.signer_reported_dt
                else None,
            }
        )
    return imzalar
