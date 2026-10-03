"""QR / doğrulama adresi çapası (plan § 4.2).

Adres güvenli istekle açılır (`core/kanit_okuma/istek.getir`, SSRF engeli).
Genel okuyucunun "en az metin" eşiği burada yok: doğrulama sayfaları çoğu
zaman kısadır (ad + belge adı). Kaydedilen gerçekler: sayfa okundu mu, alan adı
bilinen bir düzenleyenin mi, sayfada gencin adı ya da hesap e-postası geçiyor mu.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.agents.dogrulama.capalar import TUR_ADRES
from app.agents.dogrulama.kimlik import ad_eslesir
from app.core.capalar.duzenleyenler import duzenleyen
from app.core.capalar.kodlar import dogrulama_adresleri
from app.core.guvenli_istek import GuvensizAdres
from app.core.kanit_okuma.adres import normal_url
from app.core.kanit_okuma.html_ozeti import html_ozeti
from app.core.kanit_okuma.istek import getir
from app.servisler.dogrulama.capalar.temel import CapaGirdisi


async def sayfa_metni(adres: str, transport: httpx.AsyncBaseTransport | None) -> str | None:
    """Doğrulama sayfasının görünen metni; açılamazsa None."""
    try:
        sayfa = await getir(adres, transport=transport)
    except (GuvensizAdres, httpx.HTTPError, ValueError):
        return None
    if not 200 <= sayfa.durum < 300:
        return None
    if "html" in sayfa.icerik_turu.lower() or not sayfa.icerik_turu:
        ozet = html_ozeti(sayfa.metin)
        parcalar = [ozet.gorunen_baslik, ozet.aciklama, *ozet.yazarlar, ozet.metin]
        metin = " ".join(p for p in parcalar if p)
    else:
        metin = sayfa.metin
    return metin.strip() or None


class AdresDogrulayici:
    ad = TUR_ADRES

    async def dogrula(self, girdi: CapaGirdisi) -> list[dict[str, Any]]:
        kodlar = girdi.on_bilgi.get("kodlar", {}).get("liste", [])
        kod_metinleri = {k["metin"].strip() for k in kodlar}
        bulgular = []
        for adres in dogrulama_adresleri(kodlar, girdi.metin):
            metin = await sayfa_metni(adres, girdi.transport) or ""
            bulgular.append(
                {
                    "tur": TUR_ADRES,
                    "adres": adres,
                    "normal_adres": normal_url(adres),
                    "kaynak": "kod" if adres in kod_metinleri else "metin",
                    "okundu": bool(metin),
                    "duzenleyen": duzenleyen(adres),
                    "ad_eslesti": bool(metin) and ad_eslesir(girdi.ad, metin),
                    "eposta_eslesti": bool(metin and girdi.eposta)
                    and girdi.eposta.casefold() in metin.casefold(),
                }
            )
        return bulgular
