"""Adalet raporu (plan § 10.2). Saf fonksiyonlar: ağ, model, dosya yok.

Soru: "her meslek aynı güçte bir yolla Kanıt 3'e ulaşabiliyor mu?" (İ5).
Yalnızca dürüst (kötü niyetli olmayan) ve etiketli vakalara bakılır. Alan başına:
  - sistemin verdiği ortalama Kanıt ("—" ortalamaya ve bonusa girmez, ayrıca
    "—" oranı olarak gösterilir),
  - sistemin ulaştığı en yüksek Kanıt ve etiketin ulaşılabilir saydığı en yüksek Kanıt,
  - Kanıt 3'e ulaşan vakalar ("3'e giden yol").
Sorun işaretleri bir kapı değil, bir iştir (§ 10.2): fark büyürse alana yeni bir
yol eklenir; tavanlar düşürülmez. Bu yüzden `Karne.esikleri_geciyor_mu`'ya girmez.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from degerlendirme.olcutler import VakaSonucu
from degerlendirme.vaka import BaslikBeklentisi

# Bir alanın ortalaması dürüst vakaların genel ortalamasından bu kadar (puan) geride kalırsa
# "fark büyüdü" sayılır. Plan sayı vermiyor; bir seviye (0-3 ölçeğinde) yarısı alındı.
FARK_ESIGI = 0.5
# Bu kadardan az dürüst vakalı alanın ortalaması güvenilir sayılmaz.
EN_AZ_VAKA = 3

SORUN_UC_YOLU_YOK = "3'e giden yol yok"
SORUN_ORTALAMA_GERIDE = "ortalama genel ortalamanın belirgin altında"
SORUN_AZ_VAKA = "az vaka: ölçüm güvenilir değil"


@dataclass(frozen=True)
class AlanAdaleti:
    alan: str
    durust_vaka: int
    # Kanıtı "—" olan dürüst vaka oranı (ortalamaya girmez)
    tire_orani: float
    ortalama: float | None
    # Sistemin dürüst vakalarda verdiği en yüksek Kanıt
    en_yuksek: int | None
    # Etiketlerin kabul ettiği en yüksek Kanıt: bu alanda ulaşılabilir tavan
    ulasilabilir: int | None
    uc_yolu: tuple[str, ...]
    sorunlar: tuple[str, ...]


@dataclass(frozen=True)
class AdaletRaporu:
    genel_ortalama: float | None
    alanlar: tuple[AlanAdaleti, ...]

    @property
    def sorunlu_alanlar(self) -> tuple[AlanAdaleti, ...]:
        return tuple(a for a in self.alanlar if a.sorunlar)


def _en_yuksek_beklenen(beklenti: BaslikBeklentisi) -> int | None:
    adaylar = beklenti if isinstance(beklenti, list) else [beklenti]
    sayilar = [a for a in adaylar if a is not None]
    return max(sayilar) if sayilar else None


def adalet_hesapla(sonuclar: list[VakaSonucu], *, taslak: bool) -> AdaletRaporu:
    gruplar: dict[str, list[VakaSonucu]] = defaultdict(list)
    for s in sonuclar:
        if not s.vaka.kotu_niyetli and s.vaka.etiket(taslak) is not None:
            gruplar[s.vaka.alan.value].append(s)

    # Sonuç üretemeyen vaka sistemin "—" demesi değil, ölçümün eksiği: ortalamaya girmez.
    tum = [
        s.degerlendirme.kanit
        for g in gruplar.values()
        for s in g
        if not s.degerlendirme.hata and s.degerlendirme.kanit is not None
    ]
    genel = sum(tum) / len(tum) if tum else None

    alanlar = []
    for alan, vakalar in sorted(gruplar.items()):
        puanlar = [
            s.degerlendirme.kanit
            for s in vakalar
            if not s.degerlendirme.hata and s.degerlendirme.kanit is not None
        ]
        tire = sum(1 for s in vakalar if s.degerlendirme.kanit is None or s.degerlendirme.hata)
        ortalama = sum(puanlar) / len(puanlar) if puanlar else None
        en_yuksek = max(puanlar) if puanlar else None
        tavanlar = [
            t
            for s in vakalar
            if (t := _en_yuksek_beklenen(s.vaka.etiket(taslak).baslik("kanit"))) is not None
        ]
        ulasilabilir = max(tavanlar) if tavanlar else None
        uc_yolu = tuple(s.vaka.id for s in vakalar if s.degerlendirme.kanit == 3)

        sorunlar = []
        if not uc_yolu:
            sorunlar.append(SORUN_UC_YOLU_YOK)
        if (
            ortalama is not None
            and genel is not None
            and len(vakalar) >= EN_AZ_VAKA
            and genel - ortalama > FARK_ESIGI
        ):
            sorunlar.append(SORUN_ORTALAMA_GERIDE)
        if len(vakalar) < EN_AZ_VAKA:
            sorunlar.append(SORUN_AZ_VAKA)
        alanlar.append(
            AlanAdaleti(
                alan=alan,
                durust_vaka=len(vakalar),
                tire_orani=tire / len(vakalar),
                ortalama=ortalama,
                en_yuksek=en_yuksek,
                ulasilabilir=ulasilabilir,
                uc_yolu=uc_yolu,
                sorunlar=tuple(sorunlar),
            )
        )
    return AdaletRaporu(genel, tuple(alanlar))
