"""Elektronik imza çapası (docs/dogrulama.md § 4.2).

İmzanın gerçekleri `core/capalar/eimza.py`'den; burada kimlik gerçekleri
eklenir: belgede gencin adı geçiyor mu (`ad_eslesti`) ve imzalayan gencin
kendisi mi (`imzalayan_genc`: kendi imzaladığı belge bağımsız düzenleyen
sayılmaz, güvenilir kök olsa da en çok C).
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.agents.dogrulama.capalar import TUR_IMZA
from app.agents.dogrulama.kimlik import ad_eslesir
from app.core.capalar.eimza import guvenilir_kokler, imzalari_oku
from app.core.config import get_settings
from app.servisler.dogrulama.capalar.temel import CapaGirdisi


class ImzaDogrulayici:
    ad = TUR_IMZA

    async def dogrula(self, girdi: CapaGirdisi) -> list[dict[str, Any]]:
        if girdi.icerik_turu != "application/pdf" or b"/ByteRange" not in girdi.ham:
            return []
        kokler = guvenilir_kokler(get_settings().eimza_kok_klasoru)
        imzalar = await asyncio.to_thread(imzalari_oku, girdi.ham, kokler)
        ad_belgede = ad_eslesir(girdi.ad, girdi.metin)
        return [
            {
                "tur": TUR_IMZA,
                **imza,
                "imzalayan_genc": ad_eslesir(girdi.ad, imza.get("imzalayan")),
                # Kendi imzaladığı belgede ad eşleşmesi bağımsız bir kimlik bağı değildir.
                "ad_eslesti": ad_belgede and not ad_eslesir(girdi.ad, imza.get("imzalayan")),
            }
            for imza in imzalar
        ]
