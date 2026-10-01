"""Karne ölçütleri (plan § 10.1, § 10.2). Saf fonksiyonlar: ağ, model, dosya yok.

Kabul eşikleri:
  - sahte (kötü niyetli) vakada yanlış 3 = 0     (en kritik ölçüt)
  - başlık başına birebir uyum ≥ %80, ±1 uyum ≥ %95
  - notta dil ihlali = 0
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.core.kullanici_dili import metin_ihlalleri
from degerlendirme.degerlendirici import Degerlendirme
from degerlendirme.vaka import BASLIKLAR, BaslikBeklentisi, Vaka

BIREBIR_ESIGI = 0.80
YAKIN_ESIGI = 0.95


def _adaylar(beklenti: BaslikBeklentisi) -> list[int | None]:
    return list(beklenti) if isinstance(beklenti, list) else [beklenti]


def uyuyor_mu(beklenti: BaslikBeklentisi, deger: int | None) -> bool:
    """Değer beklentiyle birebir uyuşuyor mu? ("—" yalnızca "—" ile uyuşur.)"""
    return deger in _adaylar(beklenti)


def yakin_mi(beklenti: BaslikBeklentisi, deger: int | None) -> bool:
    """±1 içinde mi? "—" ile sayı arasında yakınlık yoktur: biri değerlendirmiş, öteki değil."""
    if uyuyor_mu(beklenti, deger):
        return True
    if deger is None:
        return False
    return any(a is not None and abs(a - deger) <= 1 for a in _adaylar(beklenti))


def yanlis_uc_mu(beklenti: BaslikBeklentisi, deger: int | None) -> bool:
    """Sistem 3 verdi ama beklenti 3'ü kabul etmiyor: hak edilmemiş tam puan."""
    return deger == 3 and not uyuyor_mu(beklenti, deger)


@dataclass(frozen=True)
class VakaSonucu:
    vaka: Vaka
    degerlendirme: Degerlendirme


@dataclass(frozen=True)
class BaslikOlcutu:
    birebir: float
    yakin: float
    sayi: int


@dataclass
class Karne:
    degerlendirici: str
    taslak: bool
    toplam_vaka: int
    olculen_vaka: int
    basliklar: dict[str, BaslikOlcutu]
    sahte_yanlis_uc: list[str] = field(default_factory=list)
    yanlis_uc: list[str] = field(default_factory=list)
    # Alan → Kanıt başlığında "—" oranı (okunamayan / değerlendirilmeyen)
    alan_tire_orani: dict[str, float] = field(default_factory=dict)
    # Alan → dürüst vakalarda ortalama Kanıt (adalet)
    alan_kanit_ortalamasi: dict[str, float] = field(default_factory=dict)
    not_ihlalleri: dict[str, list[str]] = field(default_factory=dict)
    hatalar: dict[str, str] = field(default_factory=dict)
    sonuclar: list[VakaSonucu] = field(default_factory=list)

    @property
    def esikleri_geciyor_mu(self) -> bool:
        return (
            self.olculen_vaka > 0
            and not self.sahte_yanlis_uc
            and not self.not_ihlalleri
            and all(
                o.birebir >= BIREBIR_ESIGI and o.yakin >= YAKIN_ESIGI
                for o in self.basliklar.values()
                if o.sayi
            )
        )


def karne_hesapla(degerlendirici: str, sonuclar: list[VakaSonucu], *, taslak: bool) -> Karne:
    """Etiketli (taslakta: önerili) vakalardan karneyi çıkarır.

    Hata veren vaka (zaman aşımı, kaset eksik) ölçüme girer ve her başlıkta
    "uyuşmadı" sayılır: sonuç üretemeyen sistem doğru sonuç üretmiş sayılmaz.
    """
    olculen = [s for s in sonuclar if s.vaka.etiket(taslak) is not None]

    sayaclar: dict[str, list[int]] = {b: [0, 0, 0] for b in BASLIKLAR}  # birebir, yakın, sayı
    karne = Karne(
        degerlendirici=degerlendirici,
        taslak=taslak,
        toplam_vaka=len(sonuclar),
        olculen_vaka=len(olculen),
        basliklar={},
        sonuclar=sonuclar,
    )

    for s in sonuclar:
        if s.degerlendirme.hata:
            karne.hatalar[s.vaka.id] = s.degerlendirme.hata
        if s.degerlendirme.not_metni:
            ihlal = metin_ihlalleri(s.degerlendirme.not_metni, hitap="sen")
            if ihlal:
                karne.not_ihlalleri[s.vaka.id] = ihlal

    tire: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    kanit_toplam: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for s in olculen:
        beklenen = s.vaka.etiket(taslak)
        assert beklenen is not None
        for baslik in BASLIKLAR:
            beklenti = beklenen.baslik(baslik)
            deger = None if s.degerlendirme.hata else s.degerlendirme.baslik(baslik)
            sayac = sayaclar[baslik]
            sayac[2] += 1
            if not s.degerlendirme.hata:
                sayac[0] += uyuyor_mu(beklenti, deger)
                sayac[1] += yakin_mi(beklenti, deger)
            if yanlis_uc_mu(beklenti, deger):
                karne.yanlis_uc.append(f"{s.vaka.id}:{baslik}")
                if s.vaka.kotu_niyetli:
                    karne.sahte_yanlis_uc.append(f"{s.vaka.id}:{baslik}")

        alan = s.vaka.alan.value
        tire[alan][1] += 1
        tire[alan][0] += s.degerlendirme.kanit is None
        if not s.vaka.kotu_niyetli and s.degerlendirme.kanit is not None:
            kanit_toplam[alan][0] += s.degerlendirme.kanit
            kanit_toplam[alan][1] += 1

    karne.basliklar = {
        b: BaslikOlcutu(
            birebir=(c[0] / c[2]) if c[2] else 0.0, yakin=(c[1] / c[2]) if c[2] else 0.0, sayi=c[2]
        )
        for b, c in sayaclar.items()
    }
    karne.alan_tire_orani = {a: t[0] / t[1] for a, t in sorted(tire.items())}
    karne.alan_kanit_ortalamasi = {a: k[0] / k[1] for a, k in sorted(kanit_toplam.items()) if k[1]}
    return karne
