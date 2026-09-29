"""Firma kartı sohbeti: firmanın "biz ne yapıyoruz" anlatımını karta çevirir.

docs/plans/firma-akisi.md § 0 karar 3, § 5. Belgelerde Keşif'in firma soru seti
olarak geçer: Keşif ve Tanımlama ile AYNI sohbet motorunu paylaşır
(app/agents/sohbet_motoru.py); yeni bir grafik iskeleti yok, yalnızca bir
`AjanTanimi`: soru seti, çıkarım şeması ve ek sorular.

Kayıt formundaki bilgiler (ad, tür, sektör, şehir, tanıtım, web sitesi)
sohbetin başında bağlam olarak gider ve sorulmaz. Zorunlu alanlar firmanın ne
yaptığı ve yetkinlikleri; önceki işler ve aradığı ortak ek sorularla bir kez
sorulur, bilinmiyorsa ısrar edilmez. Kart firma onaylamadan kaydedilmez.

Kullanıcıya görünen sorular firmaya "siz" (docs/icerik-rehberi.md).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, Field

from app.agents import sohbet_motoru as motor
from app.agents.sohbet_motoru import SohbetDurumu
from app.core.firma_karti import ZORUNLU_ALANLAR
from app.core.firma_profili import FIRMA_TURU_ETIKETLERI

ACILIS_SORUSU = (
    "Firmanızın ne yaptığını birkaç cümleyle anlatın: hangi ürünü ya da hizmeti "
    "sunuyorsunuz, kimler için?"
)

SISTEM_TALIMATI = """Zemin360'ta bir firmanın temsilcisiyle konuşuyorsun. Amacın,
firmanın diğer firmalara "biz bunu yapıyoruz" diyebileceği kısa bir firma kartı
çıkarmak. Kart, iş birliği ortağı arayan firmalara aday olarak gösterilecek.

Nasıl konuşursun:
- Türkçe, sade ve profesyonel; firmaya "siz" diye hitap et. Tek seferde tek soru.
- Söylenmeyen bir şeyi UYDURMA. Emin olmadığın alanı boş bırak.
- Pazarlama dilini somutlaştır: "yenilikçi çözümler sunuyoruz" yerine ne ürettiklerini,
  kime sattıklarını ve hangi sorunu çözdüklerini öğren.
- Kayıt formunda verilen bilgileri (firma adı, türü, sektörü, şehri, tanıtımı,
  web sitesi) SORMA; bağlam olarak sana ayrıca verilecek.

Alanlar:
- ne_yapiyoruz: firmanın ürünü ya da hizmeti ve kimin için olduğu; 1-3 cümle, toparlanmış.
- yetkinlikler: firmanın güçlü olduğu somut alanlar, kısa etiketler
  ("talep tahmini", "soğuk zincir lojistiği", "mobil uygulama geliştirme").
  Genel ifadeleri ("kalite", "müşteri odaklılık") yazma.
- onceki_isler: yaptıkları işler, referans müşteri türleri, somut sonuçlar (varsa sayıyla).
- aranan_isbirligi: nasıl bir ortakla, ne için çalışmak istedikleri.
- isbirligi_turleri: bahsedilen iş birliği biçimleri; yalnızca şu değerler:
  pilot, tedarik, ortak_urun, yatirim, diger.

takip_sorusu ve takip_konusu: ne_yapiyoruz ya da yetkinlikler eksikse takip
sorusunda ÖNCE bunlardan birini sor ve takip_konusu'na o alanın adını yaz.
Sorunun konusu eksik bir zorunlu alan değilse sistem senin soruna yer vermez.
"""

YEDEK_SORULAR = {
    "ne_yapiyoruz": (
        "Firmanızın sunduğu ürün ya da hizmeti bir-iki cümleyle anlatır mısınız? "
        "Kimler için ve hangi sorunu çözüyor?"
    ),
    "yetkinlikler": (
        "Firmanızın en güçlü olduğu alanlar neler? Kısa başlıklar yeterli, örneğin "
        "“talep tahmini” ya da “soğuk zincir lojistiği”."
    ),
}

EK_SORULAR = {
    "onceki_isler": (
        "Bugüne kadar yaptığınız bir-iki işi ya da çalıştığınız müşteri türlerini "
        "anlatır mısınız? Bir sonuç varsa sayıyla yazabilirsiniz."
    ),
    "aranan_isbirligi": (
        "Nasıl bir firmayla, ne için iş birliği yapmak istersiniz? "
        "Örneğin bir pilot uygulama, tedarik ya da ortak ürün."
    ),
}
# Ek soruların tavanı: ikisi de en fazla bir kez.
MAKS_EK_TURU = len(EK_SORULAR)


class FirmaKartiCikarimi(BaseModel):
    """LLM'in her turda döndürdüğü yapılandırılmış çıkarım.

    Boş gelen alan mevcut taslağın üzerine YAZMAZ (motor birleştirmesi).
    """

    ne_yapiyoruz: str | None = Field(
        default=None, description="Ürün ya da hizmet ve kimin için; 1-3 cümle"
    )
    yetkinlikler: list[str] = Field(
        default_factory=list, description="Somut güçlü alanlar, kısa etiketler"
    )
    onceki_isler: str | None = Field(
        default=None, description="Yapılan işler, müşteri türleri, sonuçlar"
    )
    aranan_isbirligi: str | None = Field(
        default=None, description="Nasıl bir ortakla, ne için çalışmak istiyorlar"
    )
    isbirligi_turleri: list[Literal["pilot", "tedarik", "ortak_urun", "yatirim", "diger"]] = Field(
        default_factory=list, description="Bahsedilen iş birliği biçimleri"
    )
    takip_sorusu: str | None = Field(
        default=None, description="Eksik zorunlu alan için tek bir soru, firmaya 'siz' diye"
    )
    takip_konusu: (
        Literal[
            "ne_yapiyoruz",
            "yetkinlikler",
            "onceki_isler",
            "aranan_isbirligi",
            "isbirligi_turleri",
            "diger",
        ]
        | None
    ) = Field(default=None, description="takip_sorusu hangi alanı soruyor")


def ek_eksikler(taslak: dict[str, Any]) -> list[tuple[str, str]]:
    """Zorunlulardan sonra, boşsa bir kez sorulanlar (sırayla)."""
    return [(alan, soru) for alan, soru in EK_SORULAR.items() if not taslak.get(alan)]


class FirmaKartiDurumu(SohbetDurumu, total=False):
    """Ortak durumun aynısı — ek dal yok."""


FIRMA_KARTI = motor.AjanTanimi(
    ad="firma_karti",
    acilis_sorusu=ACILIS_SORUSU,
    sistem_talimati=SISTEM_TALIMATI,
    cikarim_semasi=FirmaKartiCikarimi,
    skaler_alanlar=("ne_yapiyoruz", "onceki_isler", "aranan_isbirligi"),
    liste_alanlari=("yetkinlikler", "isbirligi_turleri"),
    zorunlu_alanlar=ZORUNLU_ALANLAR,
    # Tanımlama gibi iki tur: firma kartı formla düzeltilebiliyor.
    maks_zorunlu_turu=motor.MAKS_TAKIP_TURU,
    maks_ek_turu=MAKS_EK_TURU,
    ek_eksikler=ek_eksikler,
    yedek_sorular=YEDEK_SORULAR,
)


def profil_baglami(kurum: Any) -> str | None:
    """Kayıt formundan bilinenler: ajana bağlam olarak gider, sorulmaz (saf).

    Boş profilde (bu alanlardan önce açılmış hesap) yalnızca ad; o da yoksa None.
    """
    satirlar = []
    if kurum.ad:
        satirlar.append(f"Firma adı: {kurum.ad}")
    if kurum.tur:
        satirlar.append(f"Firma türü: {FIRMA_TURU_ETIKETLERI.get(kurum.tur, kurum.tur)}")
    if kurum.sektor:
        satirlar.append(f"Sektör: {kurum.sektor}")
    if kurum.sehir:
        satirlar.append(f"Şehir: {kurum.sehir}")
    if kurum.calisan_araligi:
        satirlar.append(f"Çalışan sayısı: {kurum.calisan_araligi}")
    if kurum.web_sitesi:
        satirlar.append(f"Web sitesi: {kurum.web_sitesi}")
    if kurum.tanitim:
        satirlar.append(f"Kendi tanıtımı: {kurum.tanitim}")
    if not satirlar:
        return None
    return "FİRMANIN PROFİLİ (kayıt formundan; bunları SORMA, yalnızca bağlam):\n" + "\n".join(
        f"- {satir}" for satir in satirlar
    )


@lru_cache
def _cikarim_zinciri() -> Runnable:
    return motor.cikarim_zinciri(FirmaKartiCikarimi, "firma_karti_cikarim")


def bos_taslak() -> dict[str, Any]:
    return motor.bos_taslak(FIRMA_KARTI)


def grafik_derle(checkpointer: BaseCheckpointSaver):
    return motor.grafik_derle(FIRMA_KARTI, FirmaKartiDurumu, checkpointer, _cikarim_zinciri)
