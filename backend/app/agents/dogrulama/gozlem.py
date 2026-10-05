"""Gözlem özetleri (plan § 10.3). Saf: sayım satırlarından panel görünümü.

Veritabanı yalnızca (platform, erişim, sayı) üçlülerini verir; oranlar ve
sıralama burada, böylece panelin her sayısı sınanabilir.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.core.kanit_okuma.belge import ErisimDurumu


@dataclass(frozen=True)
class PlatformErisimi:
    platform: str
    toplam: int
    # Erişim durumu adı → okuma sayısı (her durum yazılır, 0 olanlar dahil)
    erisimler: dict[str, int] = field(default_factory=dict)

    @property
    def acik_orani(self) -> float:
        return self.erisimler.get(ErisimDurumu.ACIK.value, 0) / self.toplam if self.toplam else 0.0


def erisim_dagilimi(satirlar: Iterable[tuple[str, str, int]]) -> list[PlatformErisimi]:
    """(platform, erişim, sayı) → platform başına dağılım; en çok okunan platform önce."""
    platformlar: dict[str, dict[str, int]] = defaultdict(lambda: {e.value: 0 for e in ErisimDurumu})
    for platform, erisim, sayi in satirlar:
        platformlar[platform][erisim] = platformlar[platform].get(erisim, 0) + sayi
    sonuc = [PlatformErisimi(p, sum(e.values()), e) for p, e in platformlar.items()]
    return sorted(sonuc, key=lambda d: (-d.toplam, d.platform))


def servis_adi(ham: str) -> str:
    """Sağlayıcıya özgü kayıt adlarını panelin servis adına indirger (oauth_github → oauth)."""
    return "oauth" if ham.startswith("oauth_") else ham
