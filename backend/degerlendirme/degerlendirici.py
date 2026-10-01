"""Değerlendirici arayüzü ve sonucu.

Karne hangi sistemi ölçtüğünü bilmez: her sistem sürümü (bugünkü rubrik,
yeni çekirdek) bu arayüzü uygulayan bir adaptördür. Böylece aynı vakalar ve
aynı ölçütler sürümler arasında karşılaştırılabilir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from degerlendirme.vaka import Vaka


@dataclass(frozen=True)
class Degerlendirme:
    """Bir vakanın sistemdeki sonucu. Başlıkta None = "—"."""

    kanit: int | None = None
    sonuc: int | None = None
    rol: int | None = None
    referans: int | None = None
    not_metni: str | None = None
    # Sistem sonuç üretemediyse nedeni (zaman_asimi, kaset_eksik, istisna adı).
    hata: str | None = None
    ayrinti: dict[str, Any] = field(default_factory=dict)

    def baslik(self, ad: str) -> int | None:
        return getattr(self, ad)

    def ozet(self) -> dict[str, Any]:
        """Gerileme karşılaştırmasında kullanılan alanlar (not metni hariç: modelin cümlesi)."""
        return {
            "kanit": self.kanit,
            "sonuc": self.sonuc,
            "rol": self.rol,
            "referans": self.referans,
            "hata": self.hata,
        }


class Degerlendirici(Protocol):
    ad: str

    async def degerlendir(self, vaka: Vaka) -> Degerlendirme: ...
