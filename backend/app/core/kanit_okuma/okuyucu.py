"""Okuyucu sözleşmesi (Strategy) ve okuma bağlamı (plan § 5.1).

Her platform bir okuyucudur: `uygun_mu` adresi tanır, `oku` belgeyi döner ya da
`None` ("ben okuyamadım, sıradakine geç"). Yeni platform = yeni sınıf + kayıt
listesine bir satır (`__init__.py`); mevcut kod değişmez.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.kanit_okuma.belge import HesapIzi, KanitBelgesi


@dataclass(frozen=True)
class OkumaBaglami:
    # Testler ve değerlendirme seti kayıtlı yanıtları verir (kaset).
    transport: httpx.AsyncBaseTransport | None = None
    github_token: str = ""


class Okuyucu(Protocol):
    ad: str

    def uygun_mu(self, url: httpx.URL) -> bool: ...

    async def oku(self, url: httpx.URL, baglam: OkumaBaglami) -> KanitBelgesi | None: ...


def metni_kur(*satirlar: tuple[str, str | None], govde: str = "") -> str:
    """Modele giden okunur metin: dolu "Etiket: değer" satırları ve gövde."""
    ust = [f"{etiket}: {deger}" for etiket, deger in satirlar if deger and str(deger).strip()]
    return "\n".join([*ust, *([""] if ust and govde else []), govde]).strip()


def hesap_izleri(
    saglayici: str, sahip: str | None, oranlar: dict[str, float]
) -> tuple[HesapIzi, ...]:
    """Repo sahibi ve katkıcılar, commit paylarıyla (repo platformlarında ortak)."""
    izler = [HesapIzi(saglayici, k, oran) for k, oran in oranlar.items()]
    if sahip and sahip not in oranlar:
        izler.insert(0, HesapIzi(saglayici, sahip, None))
    return tuple(izler)
