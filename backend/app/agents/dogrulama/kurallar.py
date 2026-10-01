"""Doğrulamanın saf kuralları: referans puanı, üçüncü taraf onayı, yeniden
isteme ve otomatik puanlama. LLM, ağ ve veritabanı yok; tabloyla test edilir.
"""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.agents.dogrulama.referans_durumu import DURUM_BEKLIYOR, DURUM_YANITLANDI

# 1-5 referans skalasını rubriğin 0-3 aralığına indirger.
# 3 ("ne iyi ne kötü") bir onay değildir, o yüzden 2'den fazlasını vermiyor;
# tam puan yalnızca açık bir olumlu referansta (5) veriliyor.
REFERANS_PUAN_ESLEMESI = {1: 0, 2: 1, 3: 1, 4: 2, 5: 3}


def referans_puanina_cevir(skala_1_5: int) -> int:
    """Referansın 1-5 puanını rubriğin 0-3 aralığına indirger."""
    if skala_1_5 not in REFERANS_PUAN_ESLEMESI:
        raise ValueError("Referans puanı 1-5 aralığında olmalı")
    return REFERANS_PUAN_ESLEMESI[skala_1_5]


def ucuncu_taraf_onayi_hesapla(puanlar: Sequence[int]) -> int | None:
    """Yanıtlamış tüm referanslardan tek bir 0-3 puanı üretir; yanıt yoksa None ("—").

    "Yanıt yok" ile "olumsuz yanıt" (0) ayrı şeylerdir: ikisi de 0 olsaydı
    referans istememiş genç, olumsuz yanıt almış gibi görünürdü (bulgu 19).

    Ortalama alınıyor, en yüksek değil: en yüksek, "olumlu diyen birini
    bulana kadar referans sor" davranışını ödüllendirirdi. Ortalama, zayıf
    bir referansın puanı aşağı çekmesine izin verir — göstergenin işi
    sinyal taşımak, parlatmak değil.

    Ortalama normal (0.5 yukarı) yuvarlanıyor: aşağı yuvarlamak iki güçlü
    referansı (5+4 → 2.5 → 2) tek bir 5'ten (3) daha düşük gösteriyordu.
    Referans eklemek puanı düşürmemeli. Python'ın round()'u 2.5'i 2'ye
    çevirdiği için (bankacı yuvarlaması) elle +0.5 uygulanıyor.
    """
    if not puanlar:
        return None
    cevrilmis = [referans_puanina_cevir(p) for p in puanlar]
    return math.floor(sum(cevrilmis) / len(cevrilmis) + 0.5)


ZATEN_BEKLENIYOR = "Bu kişiden yanıt zaten bekleniyor."


def referans_yeniden_istenebilir_mi(
    *, durum: str, guncel: bool, ayni_kisiden_bekleyen_var: bool
) -> str | None:
    """ "Referansı yeniden iste" bu istek için anlamlı mı? Değilse nedeni (409).

    Anlamlı olduğu durumlar: yanıt iş kaleminin önceki hâline verildi (geçmiş),
    ya da süresi doldu (yanıt yok). Aynı kişiden güncel bir yanıt zaten
    bekleniyorsa ikinci istek açılmaz.
    """
    if ayni_kisiden_bekleyen_var:
        return ZATEN_BEKLENIYOR
    if durum == DURUM_BEKLIYOR:
        return ZATEN_BEKLENIYOR
    if durum == DURUM_YANITLANDI and guncel:
        return "Bu referans işin güncel hâli için zaten yanıt verdi."
    return None


def otomatik_puanlanir_mi(kanit_linki: str | None, puanlanmis: bool) -> bool:
    """Kart onayı ya da düzenlemesinden sonra bu iş kalemi arka planda puanlanır mı?

    Yalnızca linki olan ve henüz puanı olmayan (ya da içeriği değişip puanı
    sıfırlanan) kalem. Linksiz kalem puanlanmaz, "doğrulanmamış" nötr durumda
    kalır: kanıtsız kalem ceza almaz, bonus da almaz (plan § 0, karar 7).
    """
    return bool(kanit_linki and kanit_linki.strip()) and not puanlanmis


# --- Referans yanıtının geçerliliği (docs/plans/genc-akisi.md § 0, karar 8) ---------
# İş kalemi değişince eski yanıt geçmişte kalır, puana girmez. Kart düzenleme
# (sıfırlama) ve Doğrulama (üçüncü taraf onayı) aynı kuralı buradan kullanır.


@dataclass(frozen=True)
class ReferansYaniti:
    puan: int | None
    yanit_tarihi: dt.datetime | None


def referans_gecerli_mi(
    yanit_tarihi: dt.datetime | None, icerik_tarihi: dt.datetime | None
) -> bool:
    """Bu referans yanıtı iş kaleminin güncel hâli için mi verildi?

    İçerik hiç değişmediyse (NULL) bütün yanıtlar geçerli, eski satırlar dahil.
    Değiştiyse yalnızca değişiklikten sonra verilen yanıt geçerli; tarihi
    bilinmeyen eski yanıt geçmişte kalır.
    """
    if icerik_tarihi is None:
        return True
    return yanit_tarihi is not None and yanit_tarihi >= icerik_tarihi


def gecerli_referans_puanlari(
    yanitlar: Iterable[ReferansYaniti], icerik_tarihi: dt.datetime | None
) -> list[int]:
    """Üçüncü taraf onayına girecek puanlar (yanıtlanmış ve güncel)."""
    return [
        y.puan
        for y in yanitlar
        if y.puan is not None and referans_gecerli_mi(y.yanit_tarihi, icerik_tarihi)
    ]
