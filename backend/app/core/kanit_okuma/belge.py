"""Kanıtın değer türleri (plan § 2, § 5.2, § 13).

Veritabanında düz metin olarak saklanır (projedeki `durum` alanlarıyla aynı
alışkanlık); anlamları ve geçerli değerleri burada, tek yerde.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ParcaTuru(StrEnum):
    """Bir iş kalemine eklenebilen kanıt parçası."""

    LINK = "link"
    DOSYA = "dosya"
    GORSEL = "gorsel"


class ErisimDurumu(StrEnum):
    """Kanıtın okunabildiği ölçü (plan § 5.2). Puanı belirler:
    `BULUNAMADI` ve `GUVENSIZ` Kanıt 0; okunamayan türler "—" (ceza değil)."""

    ACIK = "acik"
    GIRIS_GEREKLI = "giris_gerekli"
    ENGELLENDI = "engellendi"
    ICERIK_YOK = "icerik_yok"
    BULUNAMADI = "bulunamadi"
    GUVENSIZ = "guvensiz"
    HATA = "hata"

    @property
    def okunamadi_mi(self) -> bool:
        """İçerik görülemedi ama "yok" da denemez: puan "—" kalır."""
        return self in _OKUNAMAYANLAR


_OKUNAMAYANLAR = frozenset(
    {
        ErisimDurumu.GIRIS_GEREKLI,
        ErisimDurumu.ENGELLENDI,
        ErisimDurumu.ICERIK_YOK,
        ErisimDurumu.HATA,
    }
)


class KaynakSeviyesi(StrEnum):
    """Kanıtın kaynağının bağımsızlığı (plan § 2). Puan tavanını belirler.

    A `DUZENLEYEN` > B `PLATFORM` > C `KAMUYA_ACIK` > D `BEYAN`.
    """

    DUZENLEYEN = "duzenleyen"
    PLATFORM = "platform"
    KAMUYA_ACIK = "kamuya_acik"
    BEYAN = "beyan"


class SahiplikKaynagi(StrEnum):
    """Parçanın gence ait olduğunu neyin gösterdiği (ad değişikliğinde yeniden
    değerlendirilecek parçaları bulmak için de kullanılır; plan § 6.3)."""

    OAUTH = "oauth"
    PROFIL_KODU = "profil_kodu"
    AD = "ad"
    EPOSTA = "eposta"
    YOK = "yok"


@dataclass(frozen=True)
class HesapIzi:
    """Kanıtta görünen bir platform hesabı (sahiplik sinyali, plan § 6).

    Kanıtın adresinden (`medium.com/@ayse`), platformun yanıtından (oEmbed yazar
    adresi) ya da platform verisinden (repo sahibi, katkıcılar) gelir. Gencin
    bağlı hesabıyla eşleşirse kanıt seviye B olur (`agents/dogrulama/hesap_sahipligi.py`).
    """

    saglayici: str
    kullanici_adi: str
    # Repo platformlarında bu hesabın commit payı (0-1); bilinmiyorsa None.
    katki_orani: float | None = None


@dataclass(frozen=True)
class KanitBelgesi:
    """Bir kanıt adresinin okunuşu (okuyucu zincirinin çıktısı, plan § 5.1).

    `metin` modele ve alıntı denetimine gider: platformun verisi (repo açıklaması,
    yıldız, katkıcılar, README; video başlığı ve kanalı…) okunur biçimde yazılır.
    """

    url: str
    erisim: ErisimDurumu
    platform: str = "web"
    baslik: str | None = None
    metin: str = ""
    # Sayfanın söylediği yazar adları (ad eşleşmesi, § 6.3).
    yazarlar: tuple[str, ...] = ()
    # Platformun söylediği hesaplar (sahiplik sinyali, § 6). Adresteki hesap
    # buraya yazılmaz: sahiplik kuralı onu adresten kendisi çıkarır.
    hesaplar: tuple[HesapIzi, ...] = ()
    # Platform verisi (yıldız, katkı sayıları…), yapılandırılmış.
    veri: Mapping[str, Any] = field(default_factory=dict)
    # `metin`'in platformun ölçtüğü kısmı ("Yıldız: 12"). README ya da yazının
    # kendisi değil: oradaki sayı gencin iddiasıdır (§ 2). Bağlı hesapta Sonuç'u
    # yalnızca bu kısımdaki alıntı bağımsız olarak destekler.
    platform_metni: str = ""
    # Yedek okuyucunun aldığı ekran görüntüleri (JPEG, § 5.5). Model okuması
    # değerlendirme katmanında yapılır (`agents/dogrulama/okuma.py`).
    ekran_goruntuleri: tuple[bytes, ...] = ()
