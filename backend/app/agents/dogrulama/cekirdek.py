"""Değerlendirme çekirdeği: model gerçek çıkarır, kural puanlar, şablon anlatır (plan § 11).

Tek giriş noktası `kalemi_degerlendir`. Model çağrısı dışarıdan verilir
(bağımlılığın tersine çevrilmesi): uygulama gerçek zinciri, değerlendirme seti
kayıtlı yanıtı verir; ikisi aynı kuralları işletir, iki ayrı mantık yoktur.
Veritabanı yok: servis sonucu modele yazar.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field

from app.agents.dogrulama.alinti import alinti_gecerli_mi
from app.agents.dogrulama.cikarim import KanitCikarimi
from app.agents.dogrulama.kurallar import (
    BAGIMSIZ_SEVIYELER,
    BaslikPuanlari,
    OkunanKanit,
    kanit_puani,
    rol_puani,
    sonuc_puani,
)
from app.agents.dogrulama.not_sablonu import not_yaz

# Kural ya da istem değişince artar: eski göstergeler ayırt edilir, önbellek tazelenir.
KURAL_SURUMU = "2026-10-adim4"

ISARET_ALAKASIZ = "alakasiz_kanit"


@dataclass(frozen=True)
class DegerlendirmeGirdisi:
    baslik: str
    aciklama: str | None = None
    sonuc: str | None = None
    pay: str | None = None
    yetenekler: Sequence[str] = ()
    itiraz_notu: str | None = None
    # Referansın yapılandırılmış yanıtları (4 soruluk form, adım 7): "evet" bağımsız destektir.
    referans_sonuc_evet: bool = False
    referans_pay_evet: bool = False


@dataclass(frozen=True)
class YetenekKanitSonucu:
    yetenek: str
    puan: int


@dataclass(frozen=True)
class DegerlendirmeSonucu:
    puanlar: BaslikPuanlari
    not_metni: str
    girdi_ozeti: str
    isaretler: tuple[str, ...] = ()
    destekler: tuple[dict, ...] = ()
    yetenek_kanitlari: tuple[YetenekKanitSonucu, ...] = ()
    kanit_ozeti: dict = field(default_factory=dict)


Cikarici = Callable[[dict[str, str]], Awaitable[KanitCikarimi]]


def cikarim_girdisi(girdi: DegerlendirmeGirdisi, okunan: OkunanKanit | None) -> dict[str, str]:
    """Modele giden alanlar; önbellek özeti de bunlardan hesaplanır."""
    okunabildi = okunan is not None and not okunan.erisim.okunamadi_mi and okunan.metin
    return {
        "baslik": girdi.baslik,
        "aciklama": girdi.aciklama or "(yazılmamış)",
        "sonuc": girdi.sonuc or "(yazılmamış)",
        "pay": girdi.pay or "(yazılmamış)",
        "yetenekler": ", ".join(girdi.yetenekler) or "(yok)",
        "kanit_adresi": (okunan.url if okunan and okunan.url else "(kanıt yok)"),
        "kanit_metni": okunan.metin if okunabildi else "(kanıt metni yok)",
        "itiraz_notu": girdi.itiraz_notu or "(itiraz yok)",
    }


def girdi_ozeti(alanlar: dict[str, str], okunan: OkunanKanit | None, ek: dict) -> str:
    """Aynı girdi → aynı özet → önceki sonuç (itiraz önbelleği, plan § 11.4)."""
    ham = {
        "kural": KURAL_SURUMU,
        "alanlar": alanlar,
        "erisim": okunan.erisim.value if okunan else None,
        "seviye": okunan.seviye.value if okunan else None,
        "bireysel": okunan.bireysel if okunan else None,
        **ek,
    }
    return hashlib.sha256(json.dumps(ham, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def ozet_hesapla(girdi: DegerlendirmeGirdisi, okunan: OkunanKanit | None) -> str:
    return girdi_ozeti(
        cikarim_girdisi(girdi, okunan),
        okunan,
        {"ref_sonuc": girdi.referans_sonuc_evet, "ref_pay": girdi.referans_pay_evet},
    )


async def kalemi_degerlendir(
    girdi: DegerlendirmeGirdisi, okunan: OkunanKanit | None, cikar: Cikarici
) -> DegerlendirmeSonucu:
    alanlar = cikarim_girdisi(girdi, okunan)
    cikarim = await cikar(alanlar)
    metin = alanlar["kanit_metni"] if alanlar["kanit_metni"] != "(kanıt metni yok)" else ""

    # Alıntısı tam metinde bulunmayan destek ve yetenek yok sayılır.
    destekler = [
        d
        for d in cikarim.destekler
        if d.durum == "kanitta_yok" or alinti_gecerli_mi(d.alinti, metin)
    ]

    def durum(iddia: str, aranan: str) -> bool:
        return any(d.iddia == iddia and d.durum == aranan for d in destekler)

    bagimsiz_kanit = okunan is not None and okunan.seviye in BAGIMSIZ_SEVIYELER
    kanit_celisiyor = durum("is", "celisiyor") or durum("pay", "celisiyor")
    ilgili = bool(metin) and cikarim.ilgili_mi

    kanit = kanit_puani(okunan, ilgili=ilgili, celisiyor=kanit_celisiyor)
    sonuc = sonuc_puani(
        var=cikarim.sonuc_var,
        sayisal=cikarim.sonuc_sayisal,
        olcut_acik=cikarim.sonuc_olcut_acik,
        bagimsiz_destek=girdi.referans_sonuc_evet
        or (bagimsiz_kanit and durum("sonuc", "destekleniyor")),
        celisiyor=durum("sonuc", "celisiyor"),
    )
    bireysel = (
        okunan is not None
        and okunan.bireysel
        and okunan.seviye in BAGIMSIZ_SEVIYELER
        and not cikarim.ekip_ortakligi_belirtilmis
    )
    rol = rol_puani(
        var=cikarim.pay_var,
        ozgul=cikarim.pay_ozgul,
        bagimsiz_destek=girdi.referans_pay_evet
        or bireysel
        or (bagimsiz_kanit and durum("pay", "destekleniyor")),
        celisiyor=durum("pay", "celisiyor"),
    )
    puanlar = BaslikPuanlari(kanit=kanit, sonuc=sonuc, rol=rol)

    izinli = {y.casefold(): y for y in girdi.yetenekler}
    yetenekler = tuple(
        YetenekKanitSonucu(yetenek=izinli[y.yetenek.casefold()], puan=kanit)
        for y in cikarim.kanitlanan_yetenekler
        if kanit and y.yetenek.casefold() in izinli and alinti_gecerli_mi(y.alinti, metin)
    )
    isaretler = (ISARET_ALAKASIZ,) if (metin and not cikarim.ilgili_mi) else ()

    return DegerlendirmeSonucu(
        puanlar=puanlar,
        not_metni=not_yaz(puanlar, okunan, kanit_celisiyor=kanit_celisiyor, oneri=cikarim.oneri),
        girdi_ozeti=ozet_hesapla(girdi, okunan),
        isaretler=isaretler,
        destekler=tuple(d.model_dump() for d in destekler),
        yetenek_kanitlari=yetenekler,
        kanit_ozeti={
            "erisim": okunan.erisim.value if okunan else None,
            "seviye": okunan.seviye.value if okunan else None,
            "url": okunan.url if okunan else None,
            "kural_surumu": KURAL_SURUMU,
        },
    )
