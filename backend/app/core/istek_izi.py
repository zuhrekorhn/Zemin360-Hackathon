"""İsteğin izi: IP ve tarayıcının tuzlu özeti (plan § 9, `referans_supheli`).

Ham IP ve tarayıcı bilgisi SAKLANMAZ; yalnızca uygulamanın gizli anahtarından
türeyen anahtarla HMAC özeti (geri çevrilemez, başka sistemin özetiyle
eşleştirilemez). Özetler 90 gün tutulur (Canlılık taraması siler).

IP: proxy arkasında son `X-Forwarded-For` girdisi, yani bizim
proxy'mizin gördüğü adres; başlık yoksa bağlantının adresi. Yerel, özel ağ ve
çözülemeyen adreslerin özeti alınmaz (yerel denemede herkes 127.0.0.1'dir,
eşleşmesi bir şey söylemez). Tarayıcı: `User-Agent` + `Accept-Language`.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
from dataclasses import dataclass
from typing import Any

from fastapi import Request

from app.core.config import get_settings


@dataclass(frozen=True)
class IstekIzi:
    ip: str | None
    tarayici: str | None

    def sozluk(self) -> dict[str, Any]:
        return {"ip": self.ip, "tarayici": self.tarayici}


def _anahtar() -> bytes:
    return hashlib.sha256(f"iz:{get_settings().jwt_gizli_anahtar}".encode()).digest()


def ozetle(deger: str) -> str:
    return hmac.new(_anahtar(), deger.encode(), hashlib.sha256).hexdigest()[:32]


def istemci_ipsi(request: Request) -> str | None:
    iletilen = request.headers.get("x-forwarded-for", "")
    adaylar = [a.strip() for a in iletilen.split(",") if a.strip()]
    ham = adaylar[-1] if adaylar else (request.client.host if request.client else None)
    try:
        ip = ipaddress.ip_address(ham or "")
    except ValueError:
        return None
    return None if (ip.is_private or ip.is_loopback or ip.is_link_local) else str(ip)


def istekten(request: Request) -> IstekIzi:
    ip = istemci_ipsi(request)
    ua = request.headers.get("user-agent", "").strip()
    dil = request.headers.get("accept-language", "").strip()
    return IstekIzi(
        ip=ozetle(f"ip:{ip}") if ip else None,
        tarayici=ozetle(f"ua:{ua}|{dil}") if ua else None,
    )
