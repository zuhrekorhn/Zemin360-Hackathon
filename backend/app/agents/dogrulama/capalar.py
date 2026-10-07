"""Dosyanın kaynak seviyesi: dosyanın kendisi değil, içindeki doğrulanabilir çapa kanıttır
(docs/dogrulama.md § 4.1, § 4.2, § 6.3). Saf kural.

Çapa doğrulayıcıları (`app/core/capalar/`) yalnızca gerçekleri yazar
(`kanit_parcasi.belge["capalar"]`): adres hangi alan adında, sayfada ad ya da
e-posta geçiyor mu, imza bütün mü… Seviye OKUMA ANINDA bu gerçeklerden ve
gencin o anki kimlik durumundan (e-posta doğrulandı mı, ad kilitli mi)
hesaplanır: kimlik durumu ya da kural değişirse eski dosyalar da doğru okunur.

Çapa başına A (düzenleyen) ve C (kamuya açık) koşulları:
  - adres: A = bilinen düzenleyen + (e-posta eşleşmesi ya da ad üç koşulu); C = sayfa açıldı
  - imza: A = geçerli, bütün, güvenilir kök, imzalayan genç değil + belgede ad üç koşulu;
    C = geçerli ve bütün
  - rozet: A = düzenleyen doğruladı, iptal yok + alıcı e-postası eşleşti;
    C = alıcı e-postayla tanımlanmamış
  - e-Devlet: A = GİRVAK onayladı
Bunların dışı D (beyan); çapasız dosya da D. E-posta eşleşmesi ada göre öncelikli
ve daha güçlüdür (§ 6.3): adın kilitli olmasını gerektirmez.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from app.agents.dogrulama.kimlik import ada_dayali_seviye
from app.core.kanit_okuma.belge import KaynakSeviyesi, SahiplikKaynagi

TUR_ADRES = "adres"
TUR_IMZA = "imza"
TUR_ROZET = "rozet"
TUR_EDEVLET = "edevlet"


@dataclass(frozen=True)
class KimlikDurumu:
    eposta_dogrulandi: bool = False
    ad_kilitli: bool = False


@dataclass(frozen=True)
class CapaSonucu:
    seviye: KaynakSeviyesi
    sahiplik: SahiplikKaynagi = SahiplikKaynagi.YOK


BEYAN = CapaSonucu(KaynakSeviyesi.BEYAN)
KAMUYA = CapaSonucu(KaynakSeviyesi.KAMUYA_ACIK)


def _kimlikle_a(c: Mapping[str, Any], kimlik: KimlikDurumu) -> CapaSonucu | None:
    """E-posta eşleşmesi (doğrulanmış e-posta yeter) ya da ad üç koşulu → A."""
    if c.get("eposta_eslesti") and kimlik.eposta_dogrulandi:
        return CapaSonucu(KaynakSeviyesi.DUZENLEYEN, SahiplikKaynagi.EPOSTA)
    seviye = ada_dayali_seviye(
        ad_eslesti=bool(c.get("ad_eslesti")),
        eposta_dogrulandi=kimlik.eposta_dogrulandi,
        ad_kilitli_mi=kimlik.ad_kilitli,
    )
    if seviye is KaynakSeviyesi.DUZENLEYEN:
        return CapaSonucu(KaynakSeviyesi.DUZENLEYEN, SahiplikKaynagi.AD)
    return None


def capa_sonucu(c: Mapping[str, Any], kimlik: KimlikDurumu) -> CapaSonucu:
    tur = c.get("tur")
    if tur == TUR_ADRES:
        if not c.get("okundu"):
            return BEYAN
        if c.get("duzenleyen"):
            return _kimlikle_a(c, kimlik) or KAMUYA
        return KAMUYA
    if tur == TUR_IMZA:
        if not (c.get("gecerli") and c.get("butun")):
            return BEYAN
        if c.get("guvenilir") and not c.get("imzalayan_genc"):
            return _kimlikle_a(c, kimlik) or KAMUYA
        return KAMUYA
    if tur == TUR_ROZET:
        if not c.get("dogrulandi") or c.get("iptal"):
            return BEYAN
        if c.get("eposta_eslesti") and kimlik.eposta_dogrulandi:
            return CapaSonucu(KaynakSeviyesi.DUZENLEYEN, SahiplikKaynagi.EPOSTA)
        # Alıcı başka bir e-posta: başkasının rozeti. Alıcı e-postayla değilse C.
        return BEYAN if c.get("alici_eposta_ile") else KAMUYA
    if tur == TUR_EDEVLET:
        if c.get("girvak_karari") == "onaylandi":
            return CapaSonucu(KaynakSeviyesi.DUZENLEYEN, SahiplikKaynagi.AD)
        return BEYAN
    return BEYAN


_SIRA = {KaynakSeviyesi.DUZENLEYEN: 3, KaynakSeviyesi.KAMUYA_ACIK: 1, KaynakSeviyesi.BEYAN: 0}


def dosya_sonucu(capalar: Iterable[Mapping[str, Any]], kimlik: KimlikDurumu) -> CapaSonucu:
    """En güçlü çapanın sonucu; çapa yoksa beyan (D)."""
    return max(
        (capa_sonucu(c, kimlik) for c in capalar), key=lambda s: _SIRA[s.seviye], default=BEYAN
    )


def dosya_seviyesi(belge: Mapping[str, Any], kimlik: KimlikDurumu | None = None) -> CapaSonucu:
    return dosya_sonucu(belge.get("capalar", ()), kimlik or KimlikDurumu())


# --- Belge tutarsızlığı (docs/dogrulama.md § 9 `belge_tutarsiz`)
# ---------------------------------------

NEDEN_BOZUK_IMZA = "bozuk_imza"
NEDEN_AD_ESLESMEDI = "ad_eslesmedi"


def belge_tutarsizliklari(capalar: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Çapanın söylediği belgeyle çelişen gerçekler; seviye zaten D'ye düşer, bu yalnızca
    GİRVAK'ın görmesi içindir (İ1).

      - imza: geçerli değil ya da belge imzadan sonra değişmiş;
      - doğrulama sayfası (QR'dan ya da bilinen düzenleyende) açıldı ama ne gencin
        adı ne e-postası geçiyor. Metinde geçen tanınmayan adres sayılmaz: her
        bağlantı bir doğrulama sayfası değildir.
    """
    bulgular: list[dict[str, Any]] = []
    for c in capalar:
        tur = c.get("tur")
        if tur == TUR_IMZA and not (c.get("gecerli") and c.get("butun")):
            bulgular.append({"neden": NEDEN_BOZUK_IMZA, "imzalayan": c.get("imzalayan")})
        elif (
            tur == TUR_ADRES
            and c.get("okundu")
            and (c.get("kaynak") == "kod" or c.get("duzenleyen"))
            and not (c.get("ad_eslesti") or c.get("eposta_eslesti"))
        ):
            bulgular.append({"neden": NEDEN_AD_ESLESMEDI, "adres": c.get("adres")})
    return bulgular
