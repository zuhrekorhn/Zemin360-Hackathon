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
    kalem_puani,
    kanit_puani,
    rol_puani,
    sonuc_puani,
)
from app.agents.dogrulama.not_sablonu import not_yaz
from app.core.kanit_okuma.belge import KaynakSeviyesi

# Kural ya da istem değişince artar: eski göstergeler ayırt edilir, önbellek tazelenir.
KURAL_SURUMU = "2026-10-adim8"

ISARET_ALAKASIZ = "alakasiz_kanit"


@dataclass(frozen=True)
class DegerlendirmeGirdisi:
    baslik: str
    # İddianın sahibi (kayıttaki ad): kanıttaki yazar ve hesaplarla karşılaştırma için.
    iddia_sahibi: str | None = None
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
    # Puanı veren parçanın `okunanlar` içindeki sırası
    parca: int | None = None


@dataclass(frozen=True)
class DegerlendirmeSonucu:
    puanlar: BaslikPuanlari
    not_metni: str
    girdi_ozeti: str
    isaretler: tuple[str, ...] = ()
    destekler: tuple[dict, ...] = ()
    yetenek_kanitlari: tuple[YetenekKanitSonucu, ...] = ()
    kanit_ozeti: dict = field(default_factory=dict)
    # Parça başına işaretler (`okunanlar` sırasıyla; kanıtsız kalemde boş)
    parca_isaretleri: tuple[tuple[str, ...], ...] = ()


Cikarici = Callable[[dict[str, str]], Awaitable[KanitCikarimi]]


def cikarim_girdisi(girdi: DegerlendirmeGirdisi, okunan: OkunanKanit | None) -> dict[str, str]:
    """Modele giden alanlar; önbellek özeti de bunlardan hesaplanır."""
    okunabildi = okunan is not None and not okunan.erisim.okunamadi_mi and okunan.metin
    return {
        "baslik": girdi.baslik,
        "iddia_sahibi": girdi.iddia_sahibi or "(belirtilmemiş)",
        "aciklama": girdi.aciklama or "(yazılmamış)",
        "sonuc": girdi.sonuc or "(yazılmamış)",
        "pay": girdi.pay or "(yazılmamış)",
        "yetenekler": ", ".join(girdi.yetenekler) or "(yok)",
        "kanit_adresi": _kanit_adresi(okunan),
        "kanit_metni": (okunan.model_metni or okunan.metin) if okunabildi else "(kanıt metni yok)",
        "itiraz_notu": girdi.itiraz_notu or "(itiraz yok)",
    }


def _kanit_adresi(okunan: OkunanKanit | None) -> str:
    if okunan is None:
        return "(kanıt yok)"
    if okunan.url:
        return okunan.url
    return f"yüklenen dosya: {okunan.dosya_adi or 'adsız'}"


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


def ozet_hesapla(girdi: DegerlendirmeGirdisi, okunanlar: Sequence[OkunanKanit]) -> str:
    """Kalemin özeti: parça özetlerinin sırasıyla birleşimi (parça değişirse değişir)."""
    ek = {"ref_sonuc": girdi.referans_sonuc_evet, "ref_pay": girdi.referans_pay_evet}
    parcalar = [
        girdi_ozeti(cikarim_girdisi(girdi, okunan), okunan, ek) for okunan in okunanlar or [None]
    ]
    if len(parcalar) == 1:
        return parcalar[0]
    return hashlib.sha256("|".join(parcalar).encode()).hexdigest()


@dataclass(frozen=True)
class ParcaSonucu:
    """Tek bir kanıt parçasının (ya da kanıtsız iddianın) puanlanışı."""

    puanlar: BaslikPuanlari
    isaretler: tuple[str, ...]
    destekler: tuple[dict, ...]
    # Yetenek → bu parçanın verdiği puan
    yetenekler: tuple[YetenekKanitSonucu, ...]
    celisiyor: bool
    oneri: str | None


async def parcayi_degerlendir(
    girdi: DegerlendirmeGirdisi, okunan: OkunanKanit | None, cikar: Cikarici
) -> ParcaSonucu:
    alanlar = cikarim_girdisi(girdi, okunan)
    cikarim = await cikar(alanlar)
    # Alıntı denetimi TAM metne: model seçilmiş parçaları görse de alıntı her yerden olabilir.
    okunabildi = okunan is not None and not okunan.erisim.okunamadi_mi
    metin = okunan.metin if (okunan is not None and okunabildi) else ""
    alinti_kaynagi = (
        okunan.alinti_metni if (okunabildi and okunan.alinti_metni is not None) else metin
    )

    # Alıntısı tam metinde bulunmayan destek ve yetenek yok sayılır.
    destekler = [
        d
        for d in cikarim.destekler
        if d.durum == "kanitta_yok" or alinti_gecerli_mi(d.alinti, alinti_kaynagi)
    ]

    def durum(iddia: str, aranan: str) -> bool:
        return any(d.iddia == iddia and d.durum == aranan for d in destekler)

    # Bağımsız destek (§ 2, § 11.2). Çalışmanın içindeki iddia (README, yazının
    # kendisi) hangi seviyede olursa olsun iddiadır: B'de Sonuç'u yalnızca
    # platformun ölçtüğü veri, Rol'ü yalnızca katkı oranı / bireysel kural
    # destekler; metindeki destek yalnızca düzenleyen belgesinde (A) sayılır.
    seviye = okunan.seviye if okunan is not None else None
    duzenleyen = seviye is KaynakSeviyesi.DUZENLEYEN
    platform_olcumu = (
        okunan is not None
        and seviye is KaynakSeviyesi.PLATFORM
        and any(
            d.iddia == "sonuc"
            and d.durum == "destekleniyor"
            and alinti_gecerli_mi(d.alinti, okunan.platform_metni)
            for d in destekler
        )
    )
    kanit_celisiyor = durum("is", "celisiyor") or durum("pay", "celisiyor")
    ilgili = bool(metin) and cikarim.ilgili_mi

    kanit = kanit_puani(okunan, ilgili=ilgili, celisiyor=kanit_celisiyor)
    sonuc = sonuc_puani(
        var=cikarim.sonuc_var,
        sayisal=cikarim.sonuc_sayisal,
        olcut_acik=cikarim.sonuc_olcut_acik,
        bagimsiz_destek=girdi.referans_sonuc_evet
        or platform_olcumu
        or (duzenleyen and durum("sonuc", "destekleniyor")),
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
        or (duzenleyen and durum("pay", "destekleniyor")),
        celisiyor=durum("pay", "celisiyor"),
    )

    izinli = {y.casefold(): y for y in girdi.yetenekler}
    yetenekler = tuple(
        YetenekKanitSonucu(yetenek=izinli[y.yetenek.casefold()], puan=kanit)
        for y in cikarim.kanitlanan_yetenekler
        if kanit and y.yetenek.casefold() in izinli and alinti_gecerli_mi(y.alinti, alinti_kaynagi)
    )
    return ParcaSonucu(
        puanlar=BaslikPuanlari(kanit=kanit, sonuc=sonuc, rol=rol),
        isaretler=(ISARET_ALAKASIZ,) if (metin and not cikarim.ilgili_mi) else (),
        destekler=tuple(d.model_dump() for d in destekler),
        yetenekler=yetenekler,
        celisiyor=kanit_celisiyor,
        oneri=cikarim.oneri,
    )


async def kalemi_degerlendir(
    girdi: DegerlendirmeGirdisi, okunanlar: Sequence[OkunanKanit], cikar: Cikarici
) -> DegerlendirmeSonucu:
    """Her parça ayrı puanlanır; başlık başına en güçlü parça (plan § 2: parçalar
    toplanmaz, kanıt eklemek puanı düşürmez). Not, Kanıt'ı veren parçadan yazılır.
    Kanıtsız kalemde iddia tek başına değerlendirilir (Kanıt "—")."""
    liste: list[OkunanKanit | None] = list(okunanlar) or [None]
    sonuclar = [await parcayi_degerlendir(girdi, okunan, cikar) for okunan in liste]
    puanlar = kalem_puani(s.puanlar for s in sonuclar)

    def guc(i: int) -> int:
        kanit = sonuclar[i].puanlar.kanit
        return -1 if kanit is None else kanit

    onde = max(range(len(liste)), key=guc)  # eşitlikte ilk eklenen
    okunan, lider = liste[onde], sonuclar[onde]

    en_guclu: dict[str, YetenekKanitSonucu] = {}
    for i, s in enumerate(sonuclar):
        for y in s.yetenekler:
            if y.yetenek not in en_guclu or y.puan > en_guclu[y.yetenek].puan:
                en_guclu[y.yetenek] = YetenekKanitSonucu(y.yetenek, y.puan, parca=i)

    return DegerlendirmeSonucu(
        puanlar=puanlar,
        not_metni=not_yaz(puanlar, okunan, kanit_celisiyor=lider.celisiyor, oneri=lider.oneri),
        girdi_ozeti=ozet_hesapla(girdi, okunanlar),
        isaretler=tuple(dict.fromkeys(i for s in sonuclar for i in s.isaretler)),
        destekler=tuple(d for s in sonuclar for d in s.destekler),
        yetenek_kanitlari=tuple(en_guclu.values()),
        kanit_ozeti={
            "erisim": okunan.erisim.value if okunan else None,
            "seviye": okunan.seviye.value if okunan else None,
            "sahiplik": okunan.sahiplik_kaynagi.value if okunan else None,
            "url": okunan.url if okunan else None,
            "kural_surumu": KURAL_SURUMU,
            "parcalar": [
                {
                    "url": o.url,
                    "tur": o.tur,
                    "erisim": o.erisim.value,
                    "seviye": o.seviye.value,
                    "kanit": s.puanlar.kanit,
                    "sonuc": s.puanlar.sonuc,
                    "rol": s.puanlar.rol,
                }
                for o, s in zip(liste, sonuclar, strict=True)
                if o is not None
            ],
        },
        parca_isaretleri=tuple(s.isaretler for s in sonuclar) if okunanlar else (),
    )
