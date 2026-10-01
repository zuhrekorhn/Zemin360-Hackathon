"""Dış servislerin süreç içi sağlık kaydı (plan § 14.4).

`gozlemli` sarmalayıcısı her çağrının sonucunu buraya yazar; `GET
/saglik/servisler` buradan okur. Bellekte tutulur: süreç yeniden başlayınca
sıfırlanır. Amaç GİRVAK'a "e-posta şu an gidiyor mu?" sorusunun cevabını
vermek, uzun süreli ölçüm değil (o gözlem paneli, adım 12).
"""

from __future__ import annotations

import datetime as dt
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

    def _kayit(self, servis: str) -> ServisKaydi:
        return self.servisler.setdefault(servis, ServisKaydi())

    def basari(self, servis: str) -> None:
        kayit = self._kayit(servis)
        kayit.basari_sayisi += 1
        kayit.son_basari = dt.datetime.now(dt.UTC)

    def hata(self, servis: str, hata: BaseException) -> None:
        kayit = self._kayit(servis)
        kayit.hata_sayisi += 1
        kayit.son_hata = dt.datetime.now(dt.UTC)
        kayit.son_hata_turu = type(hata).__name__

    def oku(self, servis: str) -> ServisKaydi:
        return self.servisler.get(servis, ServisKaydi())


SAGLIK = SaglikKaydi()
