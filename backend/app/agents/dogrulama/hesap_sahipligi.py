"""Kanıt gencin bağlı hesabında mı? Seviye ve bireysel kural (docs/dogrulama.md § 2, § 6).

Sahiplik yalnızca OAuth ya da profil koduyla bağlanmış hesaptan gelir (docs/dogrulama.md
§ 6): beyan edilen kullanıcı adı ya da sayfada geçen ad seviye B'ye çıkarmaz.
Saf fonksiyon: ağ ve veritabanı yok; uygulama ve değerlendirme seti aynı kuralı
kullanır.

Kanıttaki hesap izleri iki yerden gelir: kanıtın adresi (`medium.com/@ayse/…`)
ve okuyucunun bildirdiği hesaplar (oEmbed yazar adresi, repo sahibi ve
katkıcılar). Bağlı hesaplardan biriyle eşleşen iz kanıtı seviye B yapar.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.core.kanit_okuma.belge import HesapIzi, KanitBelgesi, KaynakSeviyesi, SahiplikKaynagi
from app.core.kanit_okuma.hesap_izi import Saglayici, adresteki_hesap

# Bireysel kural (§ 2): commit'lerin en az bu kadarı gencinse repo tek katkıcılıdır.
BIREYSEL_KATKI_ORANI = 0.9
# Bağlı hesaptaki sayfanın kendisi gencin işi olan platformlar: tek yazarlı yazı
# (Medium, kişisel blog) ve portfolyo (Behance, Dribbble, kişisel site). Ekip ya
# da müşteri ortaklığı sayfada yazıyorsa model bunu işaretler, kural 3'ü vermez.
# Video ve notebook listede yok: bireysel kural tablosunda geçmiyorlar.
_SAYFASI_BIREYSEL = frozenset(
    {Saglayici.MEDIUM, Saglayici.KISISEL_SITE, Saglayici.BEHANCE, Saglayici.DRIBBBLE}
)
# Katkı oranını platformun ölçtüğü yerler: bireysellik yalnızca orandan.
_REPO_PLATFORMLARI = frozenset({Saglayici.GITHUB, Saglayici.GITLAB})

YONTEM_OAUTH, YONTEM_PROFIL_KODU, YONTEM_ELLE = "oauth", "profil_kodu", "elle"
_KAYNAK = {
    YONTEM_OAUTH: SahiplikKaynagi.OAUTH,
    # GİRVAK'ın elle doğruladığı profil kodu da profil kodudur (§ 6.2).
    YONTEM_PROFIL_KODU: SahiplikKaynagi.PROFIL_KODU,
    YONTEM_ELLE: SahiplikKaynagi.PROFIL_KODU,
}


@dataclass(frozen=True)
class BagliHesapBilgisi:
    """Gencin bağlı hesabı (veritabanındaki `bagli_hesap` satırının kural için özü)."""

    saglayici: str
    kullanici_adi: str
    yontem: str
    # Platformun değişmeyen kimliği (GitHub kullanıcı no, YouTube kanal no…);
    # kullanıcı adı değişse de iz bununla eşleşebilir.
    dis_kimlik: str | None = None

    def eslesir_mi(self, iz: HesapIzi) -> bool:
        if iz.saglayici != self.saglayici:
            return False
        ad = iz.kullanici_adi.casefold()
        if self.saglayici == Saglayici.KISISEL_SITE:
            # Bağlı alan adının alt alan adları da gencin sitesi (blog.ayse.dev).
            kok = self.kullanici_adi.casefold()
            return ad == kok or ad.endswith(f".{kok}")
        return ad in {self.kullanici_adi.casefold(), (self.dis_kimlik or "").casefold()}


@dataclass(frozen=True)
class Sahiplik:
    seviye: KaynakSeviyesi
    kaynak: SahiplikKaynagi
    bireysel: bool = False


SAHIPSIZ = Sahiplik(KaynakSeviyesi.KAMUYA_ACIK, SahiplikKaynagi.YOK)


def kanit_izleri(belge: KanitBelgesi) -> tuple[HesapIzi, ...]:
    adres = adresteki_hesap(belge.url)
    return (*belge.hesaplar, *((adres,) if adres else ()))


def sahiplik_belirle(belge: KanitBelgesi, bagli: Iterable[BagliHesapBilgisi]) -> Sahiplik:
    """Herkese açık okunan kanıt C; bağlı hesapta duruyorsa B (§ 2)."""
    bagli = tuple(bagli)
    if not bagli:
        return SAHIPSIZ
    eslesen = [(iz, h) for iz in kanit_izleri(belge) for h in bagli if h.eslesir_mi(iz)]
    if not eslesen:
        return SAHIPSIZ
    # Birden çok iz eşleşirse bireysel olanı (en güçlüsü) seçilir.
    iz, hesap = max(eslesen, key=lambda e: _bireysel_mi(e[0]))
    return Sahiplik(KaynakSeviyesi.PLATFORM, _KAYNAK[hesap.yontem], _bireysel_mi(iz))


def _bireysel_mi(iz: HesapIzi) -> bool:
    if iz.saglayici in _REPO_PLATFORMLARI:
        return iz.katki_orani is not None and iz.katki_orani >= BIREYSEL_KATKI_ORANI
    return iz.saglayici in _SAYFASI_BIREYSEL
