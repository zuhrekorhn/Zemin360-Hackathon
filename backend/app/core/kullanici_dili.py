"""Kullanıcıya görünen metnin dil kuralları (docs/icerik-rehberi.md).

Dil modelinin yazdığı ve kullanıcıya olduğu gibi gösterilen her metnin
istemine (sohbet soruları, "Neden uygun?", güven göstergesi notu, plan
adımları, durum özeti, hatırlatmalar) bu blok eklenir. Rehberin sözlüğü ve
yasak kelimeleri burada tek yerde.

`metin_ihlalleri` aynı kuralların denetimidir: model çıktısı gösterilmeden
önce ve değerlendirme setinin karnesinde kullanılır.
"""

from __future__ import annotations

import re
from typing import Literal

from app.core.metin import turkce_kucult

Hitap = Literal["sen", "siz"]

KULLANICI_DILI_KURALLARI = """

Yazdığın metin kullanıcıya olduğu gibi gösterilir; şu dil kurallarına uy:
- Kendini ya da platformu "ajan" diye anma; "Keşif Ajanı" gibi adlar kullanma.
- Platformu kullanan kuruluşlara "kurum" değil "firma" de.
- Gencin yaptığı işlere "çalışma" de ("somut çıktı", "iş kalemi" deme).
- Teknik kelime kullanma: skor, puan, eşik, rubrik, embedding, vektör, model,
  pilot, milestone. Eşleşmenin gücüne "uyum", değerlendirmeye "güven göstergesi",
  iş birliğinin aşamalarına "adım" de.
- Uzun tire (—) kullanma; cümleyi nokta ya da virgülle böl.
- "İş birliği", "yapay zekâ", "e-posta" ayrı ve bu yazımla yazılır."""


# Kullanıcıya gösterilmeyen terimler (kökleriyle; Türkçe ekler de yakalanır).
# "ajans" (reklam ajansı) gerçek bir kelime, "ajan" değil; "model" ise "iş modeli"
# gibi doğal kullanımı yüzünden otomatik denetime alınmadı (istemde yasak).
_YASAK_TERIMLER: tuple[tuple[str, str], ...] = (
    ("ajan", r"\bajan(?!s)\w*"),
    ("skor", r"\bskor\w*"),
    ("puan", r"\bpuan\w*"),
    ("eşik", r"\beşi[kğ]\w*"),
    ("rubrik", r"\brubri[kğ]\w*"),
    ("embedding", r"\bembedding\w*"),
    ("vektör", r"\bvektör\w*"),
    ("pilot", r"\bpilot\w*"),
    ("milestone", r"\bmilestone\w*"),
    ("somut çıktı", r"\bsomut çıktı\w*"),
    ("iş kalemi", r"\biş kalem\w*"),
)

# "Siz" hitabı: zamir ve ikinci çoğul iyelik / kişi ekleri ("yaptığınız",
# "başınıza", "eklediniz"). "deniz", "yalnız" gibi kelimeler eşleşmez: ek
# ünlüyle başlıyor (-ınız/-iniz/-unuz/-ünüz).
_SIZ_ZAMIRLERI = frozenset({"siz", "sizin", "size", "sizi", "sizde", "sizden", "sizinle", "sizce"})
_SIZ_EKI = re.compile(r"(ınız|iniz|unuz|ünüz)(ı|i|u|ü|a|e|da|de|dan|den|ın|in|un|ün|la|le)?$")


def metin_ihlalleri(metin: str, hitap: Hitap = "sen") -> list[str]:
    """Metnin rehbere aykırı yanları; boş liste = temiz.

    Denetlenen: yasak terimler, uzun tire ve hitap (`hitap="sen"` iken "siz"
    biçimleri). Anlam denetimi değil, yüzey denetimi: kesin ihlalleri yakalar.
    """
    kucuk = turkce_kucult(metin)
    ihlaller = [f"terim: {ad}" for ad, kalip in _YASAK_TERIMLER if re.search(kalip, kucuk)]
    if "—" in metin:
        ihlaller.append("uzun tire")
    if hitap == "sen":
        siz = sorted(
            {k for k in re.findall(r"\w+", kucuk) if k in _SIZ_ZAMIRLERI or _SIZ_EKI.search(k)}
        )
        if siz:
            ihlaller.append(f"hitap: {', '.join(siz)}")
    return ihlaller
