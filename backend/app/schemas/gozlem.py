"""GİRVAK gözlem paneli şemaları (plan § 10.3)."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class PlatformErisimiYaniti(BaseModel):
    platform: str
    toplam: int
    # Erişim durumu → okuma sayısı (acik, giris_gerekli, engellendi, icerik_yok,
    # bulunamadi, guvensiz, hata)
    erisimler: dict[str, int]
    acik_orani: float


class ServisDurumuYaniti(BaseModel):
    servis: str
    # Şu an kullanılan kip (resend, log, playwright, kapali…); `servis_kipleri`
    kip: str | None
    # Pencere içindeki toplamlar (kalıcı kayıt: süreç yeniden başlasa da kaybolmaz)
    basari_sayisi: int
    hata_sayisi: int
    son_basari: dt.datetime | None
    son_hata: dt.datetime | None
    son_hata_turu: str | None


class DegerlendirmeOzetiYaniti(BaseModel):
    sayi: int
    ortalama_sure_ms: int
    girdi_token: int
    cikti_token: int


class GozlemYaniti(BaseModel):
    gun: int
    erisim: list[PlatformErisimiYaniti]
    servisler: list[ServisDurumuYaniti]
    degerlendirme: DegerlendirmeOzetiYaniti
