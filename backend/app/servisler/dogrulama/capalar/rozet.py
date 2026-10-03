"""Open Badges rozet çapası (plan § 4.2).

Barındırılan (hosted) doğrulama: iddianın adresi güvenli istekle açılır;
düzenleyenin sunduğu iddia aynı adresi taşımalı, iptal edilmemiş olmalı ve
gömülü iddiadaki alıcıyla aynı alıcıyı göstermeli. Alıcı e-postası hesap
e-postasıyla eşleşirse en güçlü sinyal (§ 6.3).

Bilinen sınır: imzalı (JWS) iddiaların imzası doğrulanmıyor (düzenleyenin açık
anahtarını getirmek gerekir); bunlar "imzalı, doğrulanmadı" olarak D kalır.
OB 3.0 (Verifiable Credentials) tanınmıyor.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.agents.dogrulama.capalar import TUR_ROZET
from app.core.capalar.duzenleyenler import duzenleyen
from app.core.capalar.rozet import alici_eslesir, iddia_adresi, iddia_json, rozet_bicimi
from app.core.guvenli_istek import GuvensizAdres
from app.core.kanit_okuma.adres import normal_url
from app.core.kanit_okuma.istek import getir
from app.servisler.dogrulama.capalar.temel import CapaGirdisi

_JSON_BASLIGI = {"Accept": "application/ld+json, application/json;q=0.9"}


async def _iddiayi_getir(
    adres: str, transport: httpx.AsyncBaseTransport | None
) -> dict[str, Any] | None:
    try:
        sayfa = await getir(adres, transport=transport, basliklar=_JSON_BASLIGI)
    except (GuvensizAdres, httpx.HTTPError, ValueError):
        return None
    if not 200 <= sayfa.durum < 300:
        return None
    try:
        deger = json.loads(sayfa.metin)
    except ValueError:
        return None
    return deger if isinstance(deger, dict) else None


class RozetDogrulayici:
    ad = TUR_ROZET

    async def dogrula(self, girdi: CapaGirdisi) -> list[dict[str, Any]]:
        veri = girdi.on_bilgi.get("rozet", {}).get("veri")
        if not veri:
            return []
        bicim = rozet_bicimi(veri)
        bulgu: dict[str, Any] = {"tur": TUR_ROZET, "bicim": bicim, "dogrulandi": False}
        gomulu = iddia_json(veri) if bicim == "iddia" else None
        adres = iddia_adresi(gomulu) if gomulu else (veri if bicim == "adres" else None)
        if not adres:
            return [bulgu]
        bulgu["adres"] = adres
        bulgu["duzenleyen"] = duzenleyen(adres)
        sunulan = await _iddiayi_getir(adres, girdi.transport)
        if sunulan is None:
            return [bulgu]
        ayni_adres = normal_url(str(sunulan.get("id", adres))) == normal_url(adres)
        alici = sunulan.get("recipient")
        ayni_alici = gomulu is None or gomulu.get("recipient") in (None, alici)
        e_posta_ile, eslesti = alici_eslesir(alici, girdi.eposta)
        rozet = sunulan.get("badge")
        bulgu.update(
            {
                "dogrulandi": ayni_adres and ayni_alici,
                "iptal": bool(sunulan.get("revoked")),
                "alici_eposta_ile": e_posta_ile,
                "eposta_eslesti": eslesti,
                "rozet_adi": rozet.get("name") if isinstance(rozet, dict) else None,
            }
        )
        return [bulgu]
