"""Dosyadaki doğrulanabilir çapalar (plan § 4.2): QR / doğrulama adresi, e-imza,
Open Badges, e-Devlet barkodu.

`capalari_dogrula` kayıtlı doğrulayıcıları sırayla çalıştırır; biri hata
verirse yalnızca o çapa eksik kalır (zarif düşüş, İ9). Ön okuyucular (QR, rozet
verisi) bu paket içe aktarılınca yükleme hattına kaydolur.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.capalar import kodlar  # noqa: F401  (ön okuyucu kaydı)
from app.servisler.dogrulama.capalar.adres import AdresDogrulayici
from app.servisler.dogrulama.capalar.temel import CapaDogrulayici, CapaGirdisi

logger = logging.getLogger("zemin360.capalar")

DOGRULAYICILAR: list[CapaDogrulayici] = [AdresDogrulayici()]


async def capalari_dogrula(girdi: CapaGirdisi) -> list[dict[str, Any]]:
    bulgular: list[dict[str, Any]] = []
    for dogrulayici in DOGRULAYICILAR:
        try:
            bulgular.extend(await dogrulayici.dogrula(girdi))
        except Exception:
            logger.warning("capa=%s dogrulanamadi", dogrulayici.ad, exc_info=True)
    return bulgular


__all__ = ["DOGRULAYICILAR", "CapaDogrulayici", "CapaGirdisi", "capalari_dogrula"]
