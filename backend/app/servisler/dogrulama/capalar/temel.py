"""Çapa doğrulayıcılarının ortak yüzü (Strategy; docs/dogrulama.md § 4.2, § 14.2).

Her doğrulayıcı dosyada kendi çapasını arar ve bulduğu her çapa için bir
gerçek kaydı döner (`{"tur": "adres", "okundu": True, ...}`). Seviyeye karar
vermez: o, okuma anında saf kuralın işi (`agents/dogrulama/capalar.py`).
Yeni çapa = yeni doğrulayıcı + `DOGRULAYICILAR`'a bir satır (`__init__.py`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx


@dataclass(frozen=True)
class CapaGirdisi:
    # Ham dosya (temizlikten önce: imza bayt aralığı, rozet verisi bozulmamış)
    ham: bytes
    icerik_turu: str
    # Belgede yazan metin (maskelenmiş) ve ön okuyucuların çıktısı
    metin: str
    on_bilgi: dict[str, Any] = field(default_factory=dict)
    # Kimlik karşılaştırması için gencin kayıtlı adı ve hesap e-postası
    ad: str | None = None
    eposta: str | None = None
    transport: httpx.AsyncBaseTransport | None = None


class CapaDogrulayici(Protocol):
    ad: str

    async def dogrula(self, girdi: CapaGirdisi) -> list[dict[str, Any]]: ...
