"""Kanıtın değer türleri (plan § 2, § 5.2, § 13).

Veritabanında düz metin olarak saklanır (projedeki `durum` alanlarıyla aynı
alışkanlık); anlamları ve geçerli değerleri burada, tek yerde.
"""

from __future__ import annotations

from enum import StrEnum


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
