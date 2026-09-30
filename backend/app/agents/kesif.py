"""Keşif Ajanı — gençle sohbet eder, konuşmayı yetenek kartı taslağına çevirir.

Grafik iskeleti, taslak birleştirme ve LLM zinciri ortak motorda
(app/agents/sohbet_motoru.py). Burada kalan her şey Keşif'e özel.

docs/agent-specs.md § 1. Sınırlar oradan geliyor; üç sayaç birbirinden ayrı:
  - Zorunlu alanlar (rol, deneyim, sektör, araçlar) eksikken en fazla 6 tur
    takip sorusu. Tavan yalnızca sonsuz döngüye karşı; gelinirse alan boş
    kalır ve genç onu taslak ekranında doldurur (yer tutucu yazılmaz).
  - Çıktı başına ölçülebilir sonuç, kişinin kendi payı ve kanıt/referans:
    ilk iki çalışmada üçü, sonrakilerde yalnızca kanıt; toplam en fazla 8
    soru, her biri BİR kez. Kullanıcı bilmiyorsa ısrar edilmez, sıradakine
    geçilir.
  - Kayıt formunda alınan bilgiler (şehir, çalışma modeli, müsaitlik, durum,
    okul) bağlam olarak verilir ve SORULMAZ (docs/plans/genc-akisi.md § 5.3).
  - "Hiç projem yok" → 2 soruluk fallback zinciri, hâlâ yoksa deneyim_seviyesi
    "potansiyel" ile kart oluşur (madde 4).
  - Kart taslağı kullanıcıya gösterilir, kaydetme onaydan sonra olur (madde 3).

Doğrulama ve puanlama bu ajanın işi değil — kanıt linki sadece toplanır,
değerlendirilmez.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from typing import Any, Literal

from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, Field

from app.agents import sohbet_motoru as motor
from app.agents.sohbet_motoru import (  # noqa: F401 — dışarıya tek kapı burası
    MAKS_TAKIP_TURU,
    HizSinirHatasi,
    SohbetDurumu,
    kullanici_mesaji,
)
from app.core import calisma_modeli, musaitlik
from app.core.genc_profili import KARIYER_ETIKETLERI
from app.core.is_kalemi import IsTuru
from app.core.kullanici_dili import KULLANICI_DILI_KURALLARI

ACILIS_SORUSU = (
    "Merhaba! Seni tanımak istiyorum. Son bir yılda bitirdiğin, sonucunu "
    "görebildiğin bir çalışmanı anlat: okuldan, işten ya da gönüllü bir işten "
    "olabilir. Ne yaptın, ne ortaya çıktı?"
)

# "Hiç projem yok" dalında sırayla sorulacak sorular (agent-specs.md § 1.4).
FALLBACK_SORULARI = (
    "Sorun değil, illa bir iş deneyimi olması gerekmiyor. Okulda üzerinde "
    "çalıştığın bir ödev, bitirme projesi ya da ders dışı bir şey var mı? "
    "Küçük de olsa olur.",
    "Peki gönüllü olarak yaptığın bir şey — bir dernekte, okulda bir kulüpte, "
    "mahallende? Ya da kendi kendine öğrenirken yaptığın bir deneme?",
)

ACIKLAMA_YEDEGI = (
    "Kesin ya da büyük bir şey olması gerekmiyor; aklına gelen ilk örneği kendi "
    "cümlelerinle yazman yeterli."
)

POTANSIYEL = "potansiyel"

ZORUNLU_ALANLAR = ("rol_alani", "deneyim_seviyesi", "sektor_ilgi_alani", "araclar_teknolojiler")

SISTEM_TALIMATI = """Zemin360'ta genç bir kullanıcıyla sohbet edip neler yaptığını öğreniyorsun.

Görevin: konuşmadan yetenek kartı alanlarını çıkarmak.
- Sektör-nötr ol: yazılımcı da, pazarlamacı da, tasarımcı da aynı kartı doldurabilir.
- Kullanıcının söylemediği bir şeyi UYDURMA. Emin olmadığın alanı boş bırak.
- Doğruluk kontrolü yapma, puanlama yapma, kanıt değerlendirme. Bu senin işin değil.
- Türkçe, sade ve sıcak konuş; tek seferde tek soru sor.

Alanlar:
- rol_alani: kullanıcının kendini konumlandırdığı alan ("mobil geliştirici",
  "sosyal medya içerik üreticisi" gibi). Teknik rol adlarını TÜRKÇELEŞTİRME:
  sektörde ve kullanıcının ağzında yaygın olan adı koru — "backend geliştirici",
  "frontend geliştirici", "full-stack geliştirici", "DevOps mühendisi"; "arka
  yüz geliştirici", "ön yüz geliştirici", "tam yığın geliştirici" DEĞİL. Aynı
  kural sorduğun sorulardaki örnekler için de geçerli.
- deneyim_seviyesi: potansiyel | baslangic | orta | ileri.
  Somut bir çıktısı yoksa "potansiyel".
- sektor_ilgi_alani: ilgilendiği sektörler.
- araclar_teknolojiler: kullandığı araç/teknoloji/yöntemler (yazılım olmak zorunda değil).
  Seviyeyi soyut sorma ("Python'da ne kadar iyisin?"); o araçla ne yaptığını
  anlattırarak ortaya çıkar.
- sertifikalar, diller: yalnızca kullanıcı kendisi söylediyse (opsiyonel; ayrıca sorma).
- somut_ciktilar: bitirdiği, sonucu olan işler: proje, staj, iş, gönüllülük, yarışma.
  * is_turu: proje | staj | is | gonulluluk | yarisma (anlatımdan açıksa).
  * kanit_linki: kullanıcı bir link verdiyse.
  * referans_email: işini doğrulayabilecek birinin e-postasını verdiyse. Uydurma.
  Her çıktı için iki şeyi de öğrenmeye çalış, ama tek seferde tek soru sor:
  * olculebilir_sonuc: sayıyla anlatılabilen bir sonuç ("kaç kişi kullandı?",
    "ne kadar zaman kazandırdı?", "kaç kayıt işliyor?").
  * kendi_rolu: ekip işiyse kullanıcının kendi payı ("hangi kısmını sen yaptın?").
  Kullanıcı bilmiyorsa ya da yoksa ISRAR ETME, boş bırak. Sayı UYDURMA.

KULLANICININ PROFİLİ ayrı bir sistem mesajında verilebilir (şehir, çalışma
modeli, müsaitlik, durum, okul). Bunları ASLA sorma; aradığı fırsat türünü
(staj, yarı zamanlı…) da sorma, müsaitlik zaten profilde.

ŞU ANA KADARKİ TASLAK da ayrı bir sistem mesajında verilir; her çalışmanın bir
kimliği var ("c1" gibi). Taslakta zaten olan bir çalışmadan bahsediliyorsa YENİ
bir çıktı açma: o çalışmanın kimliğini `kimlik` alanına yaz, eksik alanlarını
doldur. Yalnızca yeni bir çalışmada `kimlik`i boş bırak.

takip_sorusu ve takip_konusu:
- rol_alani, deneyim_seviyesi, sektor_ilgi_alani ya da araclar_teknolojiler
  eksikse takip sorusunda ÖNCE bunlardan birini sor.
- takip_konusu'na sorunun hedeflediği alanı yaz (örn. "sektor_ilgi_alani").
  Sorunun konusu bu alanlardan biri değilse sistem senin soruna yer vermez.
"""
SISTEM_TALIMATI += KULLANICI_DILI_KURALLARI

YEDEK_SORULAR = {
    "rol_alani": "Kendini hangi alanda görüyorsun? Kısaca nasıl tanımlarsın?",
    "deneyim_seviyesi": "Bu alanda ne kadar zamandır uğraşıyorsun?",
    "sektor_ilgi_alani": "Hangi sektörlerde çalışmak ilgini çeker?",
    "araclar_teknolojiler": "Hangi araçları ya da yöntemleri kullanıyorsun?",
}


class SomutCiktiTaslak(BaseModel):
    """Bir somut çıktı.

    `olculebilir_sonuc` ve `kendi_rolu` Doğrulama Ajanı'nın rubriğiyle birebir
    hizalı (agent-specs.md § 4: "ölçülebilir sonuç" ve "rol netliği"). Keşif
    bunları sormazsa rubrik puanlayacak bir şey bulamıyor — gerçek bir kart
    bu yüzden 0/3 ve 1/3 almıştı.
    """

    kimlik: str | None = Field(
        default=None,
        description="Taslakta zaten olan bir çalışmaysa onun kimliği (örn. 'c1'); yeniyse boş",
    )
    baslik: str = Field(description="Kısa başlık, örn. 'Mahalle kütüphanesi ödünç takip sistemi'")
    aciklama: str | None = Field(
        default=None,
        description="Ne yaptığı ve ortaya ne çıktığı, kullanıcının anlattığı kadarıyla",
    )
    olculebilir_sonuc: str | None = Field(
        default=None,
        description=(
            "Sayı, oran ya da süre içeren sonuç — kullanıcı söylediyse. "
            "Örn. '400 kitap ve 120 üye takip ediliyor'. Uydurma."
        ),
    )
    kendi_rolu: str | None = Field(
        default=None,
        description=(
            "Kullanıcının bu işteki kendi payı, kendi ifadesiyle. "
            "Örn. 'backend'i ben yazdım, tasarımı arkadaşım yaptı'. Uydurma."
        ),
    )
    kanit_linki: str | None = Field(default=None, description="Kullanıcı bir link verdiyse")
    is_turu: IsTuru | None = Field(
        default=None, description="proje | staj | is | gonulluluk | yarisma; açıksa"
    )
    referans_email: str | None = Field(
        default=None,
        description="İşi doğrulayabilecek kişinin e-postası, kullanıcı verdiyse. Uydurma.",
    )


class TaslakCikarimi(motor.SohbetCikarimi):
    """LLM'in her turda döndürdüğü yapılandırılmış çıkarım.

    Serbest metin parse edilmiyor; Gemini'nin structured output'u kullanılıyor.
    Bilinmeyen alanlar None/boş döner ve mevcut taslağın üzerine YAZMAZ.
    """

    rol_alani: str | None = None
    deneyim_seviyesi: Literal["potansiyel", "baslangic", "orta", "ileri"] | None = None
    sektor_ilgi_alani: list[str] = Field(default_factory=list)
    araclar_teknolojiler: list[str] = Field(default_factory=list)
    sertifikalar: list[str] = Field(default_factory=list)
    diller: list[str] = Field(default_factory=list)
    somut_ciktilar: list[SomutCiktiTaslak] = Field(default_factory=list)
    somut_cikti_yok_dedi: bool = Field(
        default=False,
        description="Kullanıcı bu turda anlatacak bir işi/projesi olmadığını söylediyse True",
    )
    takip_sorusu: str | None = Field(
        default=None,
        description="Eksik kalan alanlar için sorulabilecek tek bir doğal takip sorusu",
    )
    # Sistem, soruyu yalnızca konusu eksik bir zorunlu alansa kullanıyor
    # (sohbet_motoru.zorunlu_alan_sorusu); ölçüt/rol konusu ek fazın işi.
    takip_konusu: (
        Literal[
            "rol_alani",
            "deneyim_seviyesi",
            "sektor_ilgi_alani",
            "araclar_teknolojiler",
            "somut_ciktilar",
            "olculebilir_sonuc",
            "kendi_rolu",
            "diger",
        ]
        | None
    ) = Field(default=None, description="takip_sorusu hangi alanı soruyor")


class KesifDurumu(SohbetDurumu, total=False):
    """Ortak duruma Keşif'in fallback zinciri için iki alan ekler."""

    fallback_indeksi: int
    cikti_yok_dedi: bool


def _fallback_dali(durum: dict[str, Any]) -> dict[str, Any] | None:
    """Somut çıktı yoksa fallback zinciri (okul ödevi → gönüllü iş).

    Zincir bitmişse ya da taslakta bir çalışma varsa None döner.
    """
    fallback_indeksi = durum.get("fallback_indeksi", 0)
    if durum["taslak"].get("somut_ciktilar") or fallback_indeksi >= len(FALLBACK_SORULARI):
        return None

    return motor.soru_durumu(
        FALLBACK_SORULARI[fallback_indeksi], fallback_indeksi=fallback_indeksi + 1
    )


def _calismasiz_genc_dali(durum: dict[str, Any]) -> dict[str, Any] | None:
    """Çalışmam yok diyen gence okul ödevi ve gönüllülük soruları HEMEN.

    Eskiden bu sorular zorunlu alanlardan sonra geliyordu: çalışması olmayan
    gence önce "bu alanda ne kadar zamandır uğraşıyorsun?" soruluyordu. Bir
    ödev anlatırsa o ödev çalışma olur ve akış normal devam eder; söylemeyen
    gence zincir yine takip sorularından sonra sorulur (`ek_dal`).
    """
    return _fallback_dali(durum) if durum.get("cikti_yok_dedi") else None


def _cikti_yok_bayragi(cikarim: TaslakCikarimi, durum: Mapping[str, Any]) -> dict[str, Any]:
    """Bir kez söylenen "çalışmam yok" kalıcı: model sonraki turda yeniden
    işaretlemese de kaybolmaz."""
    return {"cikti_yok_dedi": bool(durum.get("cikti_yok_dedi")) or cikarim.somut_cikti_yok_dedi}


def _taslak_kurali(taslak: dict[str, Any], durum: Mapping[str, Any]) -> dict[str, Any]:
    """Çalışması olmadığını söyleyen gencin deneyimi "potansiyel": deneyim
    sorusu sorulmaz. Sonradan çalışma anlatırsa kapanışta potansiyel kuralı
    seviyeyi düzeltir."""
    if durum.get("cikti_yok_dedi") and not taslak.get("somut_ciktilar"):
        return {**taslak, "deneyim_seviyesi": POTANSIYEL}
    return taslak


# Sonuç, pay ve kanıt sorularının üçü de bu kadar çalışmaya sorulur; sonraki
# çalışmalara yalnızca kanıt. Eskiden sabit 4 soruluk tavan ikinci çalışmada
# bitiyor, onun payı ve kanıtı hiç sorulmuyordu. Kanıt öncelikli: Doğrulama
# yalnızca linki olan çalışmayı değerlendirebiliyor.
AYRINTILI_SORULAN_CALISMA = 2
# Ek soruların güvenlik tavanı: beş çalışması olan gence 15 soru sorulmasın.
MAKS_EK_TURU = 8


def _cikti_eksikleri(taslak: dict[str, Any]) -> list[tuple[str, str]]:
    """Çıktı başına eksik ölçüt, rol ve kanıt/referans için takip soruları.

    Zorunlu alan değiller: kullanıcı bilmiyorsa kart yine kurulur. Ama
    sorulmazsa Doğrulama Ajanı'nın bileşenleri kesin düşük kalıyor. Kanıt ve
    referans tek soruda soruluyor ki sohbet uzamasın; kanıt iş kalemine bağlı
    kaydedilir (plan § 5.4). Sıra: çalışma çalışma, her birinde sonuç → pay →
    kanıt.
    """
    return [
        soru
        for sira, cikti in enumerate(taslak.get("somut_ciktilar") or [])
        for soru in _calisma_sorulari(cikti, ayrintili=sira < AYRINTILI_SORULAN_CALISMA)
    ]


def _calisma_sorulari(cikti: dict[str, Any], *, ayrintili: bool) -> list[tuple[str, str]]:
    """Bir çalışmanın eksik bilgileri için (anahtar, soru) çiftleri."""
    baslik = cikti.get("baslik") or "bu çalışma"
    # "Soruldu" işareti kimliğe bağlı: başlık değişince soru tekrar gelmesin.
    # Kimliksiz kayıt yalnızca bu özellikten önceki taslaklarda var.
    anahtar = cikti.get(motor.KIMLIK) or baslik
    sorular: list[tuple[str, str]] = []
    if ayrintili and not cikti.get("olculebilir_sonuc"):
        sorular.append(
            (
                f"olcut:{anahtar}",
                f"“{baslik}” için sonucu sayıyla anlatabilir misin? Örneğin kaç "
                "kişi kullandı ya da ne kadar zaman kazandırdı. Bilmiyorsan geçebiliriz.",
            )
        )
    if ayrintili and not cikti.get("kendi_rolu"):
        sorular.append(
            (
                f"rol:{anahtar}",
                f"“{baslik}” üzerinde tek başına mı çalıştın, ekipçe mi? "
                "Ekipçeyse hangi kısmı sen yaptın?",
            )
        )
    if not cikti.get("kanit_linki") and not cikti.get("referans_email"):
        sorular.append(
            (
                f"kanit:{anahtar}",
                f"“{baslik}” çalışmanı gösteren bir link var mı (kod deposu, demo, "
                "yayın)? Ya da bu çalışmayı doğrulayabilecek birinin e-postası? İkisi de "
                "isteğe bağlı.",
            )
        )
    return sorular


def potansiyel_kurali(deneyim_seviyesi: str | None, cikti_sayisi: int) -> str | None:
    """Çıktısı olmayan kart "potansiyel" etiketiyle çıkar — Doğrulama Ajanı'nı
    atlayıp doğrudan Eşleştirme'ye gider (agent-specs.md § 1.4).

    İki yerde uygulanıyor ve ikisi aynı kuralı işletmeli: sohbet taslağı
    kapatırken (`_tamamla`) ve onay anında (app/api/kesif.py). İkincisi
    gerekli çünkü kullanıcı taslak ekranında tüm çıktıları "Çıkar"
    diyebiliyor; arayüz o anda "potansiyel olarak kaydedilecek" diyordu ama
    kart sohbetteki eski seviyeyle kaydediliyordu.
    """
    return POTANSIYEL if cikti_sayisi == 0 else deneyim_seviyesi


def _tamamla(taslak: dict[str, Any]) -> dict[str, Any]:
    """Taslağı kapatmadan önceki son rötuş: potansiyel kuralı.

    Boş kalan zorunlu alana yer tutucu YAZILMAZ: "belirtilmedi" rolü ve
    deneyimi karta, eşleştirme metnine ve gerekçelere giriyordu. Genç alanı
    taslak ekranında doldurur; onay boş alanı kabul etmez (OnayliKart).

    Sonuç ve rol artık açıklamaya birleştirilmiyor: iş kaleminde ayrı alanlar
    (düzenlenebilsinler diye). Rubrik ve embedding onları birleşik okuyor
    (app/core/is_kalemi.py).
    """
    son = dict(taslak)
    son["somut_ciktilar"] = list(son.get("somut_ciktilar") or [])
    son["deneyim_seviyesi"] = potansiyel_kurali(
        son.get("deneyim_seviyesi"), len(son["somut_ciktilar"])
    )
    return son


KESIF = motor.AjanTanimi(
    ad="kesif",
    acilis_sorusu=ACILIS_SORUSU,
    sistem_talimati=SISTEM_TALIMATI,
    cikarim_semasi=TaslakCikarimi,
    aciklama_yedegi=ACIKLAMA_YEDEGI,
    skaler_alanlar=("rol_alani", "deneyim_seviyesi"),
    liste_alanlari=("sektor_ilgi_alani", "araclar_teknolojiler", "sertifikalar", "diller"),
    nesne_listeleri=(
        motor.NesneListesi(alan="somut_ciktilar", anahtar="baslik", kimlik_oneki="c"),
    ),
    zorunlu_alanlar=ZORUNLU_ALANLAR,
    yedek_sorular=YEDEK_SORULAR,
    ek_eksikler=_cikti_eksikleri,
    maks_ek_turu=MAKS_EK_TURU,
    oncelikli_dal=_calismasiz_genc_dali,
    ek_dal=_fallback_dali,
    ek_cikarim_alanlari=_cikti_yok_bayragi,
    taslak_kurali=_taslak_kurali,
    tamamla=_tamamla,
)


@lru_cache
def _cikarim_zinciri() -> Runnable:
    return motor.cikarim_zinciri(TaslakCikarimi, "kesif_cikarim")


def profil_baglami(kullanici: Any) -> str | None:
    """Kayıt formundan bilinenler: ajana bağlam olarak gider, sorulmaz (saf).

    Boş profilde (bu alanlardan önce açılmış hesap) None: bağlam mesajı gitmez.
    """
    satirlar = []
    if kullanici.sehir:
        satirlar.append(f"Şehir: {kullanici.sehir}")
    if kullanici.calisma_modelleri:
        modeller = ", ".join(
            calisma_modeli.ETIKETLER.get(m, m) for m in kullanici.calisma_modelleri
        )
        satirlar.append(f"Çalışma modeli: {modeller}")
    if kullanici.musaitlikler:
        tipler = ", ".join(musaitlik.ETIKETLER.get(m, m) for m in kullanici.musaitlikler)
        satirlar.append(f"Müsaitlik (aradığı fırsat türü): {tipler}")
    if kullanici.kariyer_durumu:
        satirlar.append(
            f"Durum: {KARIYER_ETIKETLERI.get(kullanici.kariyer_durumu, kullanici.kariyer_durumu)}"
        )
    egitim = " – ".join(p for p in (kullanici.okul, kullanici.bolum) if p)
    if egitim:
        satirlar.append(f"Eğitim: {egitim}")
    if not satirlar:
        return None
    return "KULLANICININ PROFİLİ (kayıt formundan; bunları SORMA, yalnızca bağlam):\n" + "\n".join(
        f"- {satir}" for satir in satirlar
    )


def bos_taslak() -> dict[str, Any]:
    return motor.bos_taslak(KESIF)


def _birlestir(taslak: dict[str, Any], cikarim: TaslakCikarimi) -> dict[str, Any]:
    return motor.birlestir(KESIF, taslak, cikarim)


async def _karar(durum: dict[str, Any]) -> dict[str, Any]:
    return await motor.karar(KESIF, durum)


def grafik_derle(checkpointer: BaseCheckpointSaver):
    return motor.grafik_derle(
        KESIF,
        KesifDurumu,
        checkpointer,
        _cikarim_zinciri,
        ek_baslangic={"fallback_indeksi": 0},
    )
