"""Görsel kaynak aramasının kuralları (docs/dogrulama.md § 4.3, § 9 `gorsel_baskasinda`, § 14.4).
Saf.

İki soru:
  - Aranır mı? Yalnızca tasarım / fotoğraf alanındaki gençlerin görsellerinde
    (§ 14.4: servis ücretli ve görsel yurt dışına gider). Alan, kartın rol
    alanından ve araçlarından anlaşılır; eşleşme kelime bazında, Türkçe
    harflerden bağımsız.
  - Hangi sayfa "başkasında"? Görselin BİREBİR eşi olan ve gencin kendi
    hesabında (bağlı hesap) ya da kendi kanıt linklerinin hesabında olmayan
    sayfa. Kısmi / benzer eşleşme sinyal değildir (stok doku, şablon).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence

from app.agents.dogrulama.hesap_sahipligi import BagliHesapBilgisi
from app.core.dis_servisler.gorsel_arayici import EslesenSayfa
from app.core.kanit_okuma.hesap_izi import adresteki_hesap
from app.core.metin import turkce_kucult

# Rol alanında geçerse tasarım / fotoğraf alanı (aksansız, küçük harf; kelime ya da kelime başı).
ALAN_KELIMELERI = (
    "tasarim", "design", "ui", "ux", "grafik", "graphic", "illustrasyon", "illustrat",
    "fotograf", "photo", "gorsel", "visual", "sanat", "art", "artist", "3d", "animasyon",
    "animat", "motion", "logo", "marka", "brand", "moda", "fashion", "kurgu", "video",
)  # fmt: skip
# Araçlarda geçerse aynı alan (tasarım ve fotoğraf yazılımları).
ALAN_ARACLARI = (
    "figma", "photoshop", "illustrator", "lightroom", "indesign", "after effects",
    "premiere", "blender", "procreate", "sketch", "canva", "affinity", "cinema 4d",
    "davinci", "capture one", "coreldraw", "zbrush", "substance",
)  # fmt: skip


def _sade(metin: str) -> str:
    ayrik = unicodedata.normalize("NFKD", turkce_kucult(metin).replace("ı", "i"))
    return "".join(h for h in ayrik if not unicodedata.combining(h))


def gorsel_alani_mi(rol_alani: str | None, araclar: Sequence[str] = ()) -> bool:
    kelimeler = re.findall(r"[a-z0-9]+", _sade(rol_alani or ""))
    if any(k.startswith(a) for k in kelimeler for a in ALAN_KELIMELERI if len(a) > 3):
        return True
    if any(k in {a for a in ALAN_KELIMELERI if len(a) <= 3} for k in kelimeler):
        return True  # "ui", "ux", "art", "3d" yalnızca tam kelime
    arac_metni = " ".join(_sade(a) for a in araclar)
    return any(a in arac_metni for a in ALAN_ARACLARI)


def kendi_sayfasi_mi(
    adres: str, bagli: Iterable[BagliHesapBilgisi], kendi_adresleri: Iterable[str]
) -> bool:
    """Sayfa gencin bağlı hesabında ya da kanıt olarak verdiği bir hesapta mı?"""
    iz = adresteki_hesap(adres)
    if iz is None:
        return False
    if any(h.eslesir_mi(iz) for h in bagli):
        return True
    kendi = {adresteki_hesap(a) for a in kendi_adresleri}
    return any(
        k is not None
        and k.saglayici == iz.saglayici
        and k.kullanici_adi.casefold() == iz.kullanici_adi.casefold()
        for k in kendi
    )


def baskasindaki_sayfalar(
    sayfalar: Iterable[EslesenSayfa],
    bagli: Iterable[BagliHesapBilgisi],
    kendi_adresleri: Iterable[str],
) -> list[EslesenSayfa]:
    bagli, kendi_adresleri = tuple(bagli), tuple(kendi_adresleri)
    return [
        s
        for s in sayfalar
        if s.tam_eslesme and not kendi_sayfasi_mi(s.adres, bagli, kendi_adresleri)
    ]
