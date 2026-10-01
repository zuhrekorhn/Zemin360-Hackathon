"""Doğrulamanın saf kuralları: referans puanı, üçüncü taraf onayı, yeniden
isteme ve otomatik puanlama. LLM, ağ ve veritabanı yok; tabloyla test edilir.
"""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.agents.dogrulama.referans_durumu import DURUM_BEKLIYOR, DURUM_YANITLANDI
from app.core.kanit_okuma.belge import ErisimDurumu, KaynakSeviyesi

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


# --- Puan kuralları (docs/plans/dogrulama-iyilestirme.md § 2, § 11.2) ---------------------
# Model gerçekleri çıkarır (cikarim.py), puanı buradaki saf fonksiyonlar verir: aynı
# gerçekler her zaman aynı puanı üretir ve kural tabloyla test edilir.

# Kanıt başlığının seviye tavanı. Çapasız yüklenmiş dosya (D) 1; kamuya açık çalışma
# (C) 2; bağlı hesap ya da düzenleyen (B, A) 3. Yazılmış iddia metni kanıt değildir:
# hiç parça yoksa Kanıt "—".
KANIT_TAVANI: dict[KaynakSeviyesi, int] = {
    KaynakSeviyesi.BEYAN: 1,
    KaynakSeviyesi.KAMUYA_ACIK: 2,
    KaynakSeviyesi.PLATFORM: 3,
    KaynakSeviyesi.DUZENLEYEN: 3,
}
BAGIMSIZ_SEVIYELER = frozenset({KaynakSeviyesi.PLATFORM, KaynakSeviyesi.DUZENLEYEN})
CELISKI_TAVANI = 1


@dataclass(frozen=True)
class OkunanKanit:
    """Bir kanıt parçasının okunuşu (adım 5'te okuyucu zinciri üretir)."""

    erisim: ErisimDurumu
    seviye: KaynakSeviyesi
    metin: str
    url: str | None = None
    # Bağlı hesapta tek katkıcılı repo / tek yazarlı yazı / bağlı portfolyo (§ 2).
    bireysel: bool = False


@dataclass(frozen=True)
class BaslikPuanlari:
    kanit: int | None
    sonuc: int | None
    rol: int | None


def kanit_puani(okunan: OkunanKanit | None, *, ilgili: bool, celisiyor: bool) -> int | None:
    """Kanıt: iş var mı, bu kişinin mi? None = "—" (kanıt yok ya da okunamadı)."""
    if okunan is None or okunan.erisim.okunamadi_mi:
        return None
    if okunan.erisim in (ErisimDurumu.BULUNAMADI, ErisimDurumu.GUVENSIZ):
        return 0
    if not ilgili:
        return 0
    tavan = KANIT_TAVANI[okunan.seviye]
    return min(tavan, CELISKI_TAVANI) if celisiyor else tavan


def sonuc_puani(
    *, var: bool, sayisal: bool, olcut_acik: bool, bagimsiz_destek: bool, celisiyor: bool
) -> int:
    """Sonuç: açık yazılmış en çok 2; 3 için bağımsız destek (B/A kanıtı ya da referans)."""
    if not var:
        return 0
    puan = 1 if not sayisal else 3 if (olcut_acik and bagimsiz_destek) else 2
    return min(puan, CELISKI_TAVANI) if celisiyor else puan


def rol_puani(*, var: bool, ozgul: bool, bagimsiz_destek: bool, celisiyor: bool) -> int:
    """Rol: özgül yazılmış en çok 2; 3 için bağımsız destek (bireysel kural, B/A, referans)."""
    if not var:
        return 0
    puan = 1 if not ozgul else 3 if bagimsiz_destek else 2
    return min(puan, CELISKI_TAVANI) if celisiyor else puan


def kalem_puani(parcalar: Iterable[BaslikPuanlari]) -> BaslikPuanlari:
    """Başlık başına en güçlü parça; parçalar toplanmaz (kanıt eklemek puanı düşürmez)."""
    liste = list(parcalar)

    def en_guclu(degerler: Iterable[int | None]) -> int | None:
        dolu = [d for d in degerler if d is not None]
        return max(dolu) if dolu else None

    return BaslikPuanlari(
        kanit=en_guclu(p.kanit for p in liste),
        sonuc=en_guclu(p.sonuc for p in liste),
        rol=en_guclu(p.rol for p in liste),
    )
