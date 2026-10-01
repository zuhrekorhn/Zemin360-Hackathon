"""Dış servislerin tek kurulum noktası (plan § 14.2, bağımlılığın tersine çevrilmesi).

Servisler somut sınıfı tanımaz; buradaki fabrikadan alır. Hangi sınıfın
seçileceği `.env` bayraklarına bağlıdır. Testler fabrikayı sahteyle değiştirir
(`tests/conftest.py`). Yeni bir servis (depo, virüs tarayıcı…) buraya bir
fabrika ve `servis_kipleri`'ne bir satır olarak eklenir.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.dis_servisler.eposta import (
    EpostaGonderici,
    KapaliGonderici,
    LogGonderici,
    ResendGonderici,
)

logger = logging.getLogger("zemin360.dis_servisler")


@lru_cache
def eposta_gonderici() -> EpostaGonderici:
    return eposta_gondericisi_sec(get_settings())


def eposta_gondericisi_sec(ayar: Settings) -> EpostaGonderici:
    if ayar.eposta_saglayici == "kapali":
        return KapaliGonderici()
    if ayar.eposta_saglayici == "resend":
        if ayar.resend_api_key and ayar.eposta_gonderen:
            return ResendGonderici(
                api_anahtari=ayar.resend_api_key,
                gonderen=ayar.eposta_gonderen,
                zaman_asimi_sn=ayar.eposta_zaman_asimi_sn,
            )
        # Eksik ayarla açılış durmaz (İ9): kayıt sürer, bağlantı log'da görünür.
        logger.warning(
            "EPOSTA_SAGLAYICI=resend ama RESEND_API_KEY ya da EPOSTA_GONDEREN boş; log kipi"
        )
    return LogGonderici()


def servis_kipleri() -> dict[str, str]:
    """Servis adı → o an kullanılan kip (sağlık ucu için)."""
    return {"eposta": eposta_gonderici().kip}
