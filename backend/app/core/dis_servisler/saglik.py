"""Dış servislerin süreç içi sağlık kaydı (docs/dogrulama.md § 14.4).

`gozlemli` sarmalayıcısı her çağrının sonucunu buraya yazar; `GET
/saglik/servisler` buradan okur. Bellekte tutulur: süreç yeniden başlayınca
sıfırlanır. Amaç GİRVAK'a "e-posta şu an gidiyor mu?" sorusunun cevabını
vermek. Kalıcı kayıt `kalici` kancasıyla `servisler/gozlem.py`'e gider (uygulama açılışında
bağlanır, `servis_gunlugu` tablosu) ve GİRVAK gözlem panelini besler.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class ServisKaydi:
    basari_sayisi: int = 0
    hata_sayisi: int = 0
    son_basari: dt.datetime | None = None
    son_hata: dt.datetime | None = None
    # Hata sınıfının adı; mesaj değil (mesajda adres ya da anahtar olabilir).
    son_hata_turu: str | None = None


@dataclass
class SaglikKaydi:
    servisler: dict[str, ServisKaydi] = field(default_factory=dict)
    # (servis, başarılı mı, hata türü) → kalıcı günlüğe yazar; bağlı değilse bellekte kalır.
    kalici: Callable[[str, bool, str | None], None] | None = None

    def _kayit(self, servis: str) -> ServisKaydi:
        return self.servisler.setdefault(servis, ServisKaydi())

    def basari(self, servis: str) -> None:
        kayit = self._kayit(servis)
        kayit.basari_sayisi += 1
        kayit.son_basari = dt.datetime.now(dt.UTC)
        if self.kalici:
            self.kalici(servis, True, None)

    def hata(self, servis: str, hata: BaseException) -> None:
        kayit = self._kayit(servis)
        kayit.hata_sayisi += 1
        kayit.son_hata = dt.datetime.now(dt.UTC)
        kayit.son_hata_turu = type(hata).__name__
        if self.kalici:
            self.kalici(servis, False, kayit.son_hata_turu)

    def oku(self, servis: str) -> ServisKaydi:
        return self.servisler.get(servis, ServisKaydi())


SAGLIK = SaglikKaydi()
