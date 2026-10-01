"""Kanıt adresinin kimliği: aynı sayfanın farklı yazımları tek biçime iner.

Kullanım: bir kalemde aynı link iki kez eklenmesin (tekillik) ve aynı
kanıtın başka bir hesapta kullanıldığı fark edilsin (plan § 9). Getirmek için
değil: istek atılacak adres `istek.adresi_hazirla`'dan gelir.

Kurallar: şema https'e, alan adı küçük harfe ve `www.` öneksiz biçime iner;
varsayılan port, parça (#…), sondaki `/` ve izleme parametreleri (utm_*,
fbclid, gclid…) atılır; kalan parametreler sıralanır. Yol büyük/küçük harfe
duyarlı bırakılır: birçok sitede farklı sayfalardır.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit

# Kanıt linkinin en büyük uzunluğu (şema ve servis aynı sınırı kullanır).
KANIT_LINKI_UZUNLUGU = 500

_IZLEME_PARAMETRELERI = frozenset({"fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "si"})
_SEMA = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")


def normal_url(adres: str) -> str:
    link = adres.strip()
    if not _SEMA.match(link):
        link = "https://" + link.lstrip("/")
    try:
        parcalar = urlsplit(link)
        port = parcalar.port
    except ValueError:
        return link.lower()

    alan_adi = (parcalar.hostname or "").lower().removeprefix("www.")
    if port in (80, 443):
        port = None
    yol = parcalar.path.rstrip("/")
    sorgu = urlencode(
        sorted(
            (ad, deger)
            for ad, deger in parse_qsl(parcalar.query, keep_blank_values=True)
            if not ad.lower().startswith("utm_") and ad.lower() not in _IZLEME_PARAMETRELERI
        )
    )
    return f"https://{alan_adi}{f':{port}' if port else ''}{yol}{f'?{sorgu}' if sorgu else ''}"
