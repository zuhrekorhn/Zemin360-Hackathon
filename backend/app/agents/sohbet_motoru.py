"""Keşif ve Tanımlama ajanlarının paylaştığı sohbet motoru.

docs/agent-specs.md § 2: "Keşif Ajanı ile aynı sohbet motorunu paylaşır
(ayrı yazılmaz), sadece soru seti farklıdır."

Motorun bildiği üç şey var:
  1. Grafik iskeleti — açılış → yapılandırılmış çıkarım → karar düğümü.
  2. Taslak birleştirme — skaler alan üzerine yazar, liste alanı tekrarsız
     ekler, boş gelen çıkarım eski değeri SİLMEZ. Nesne listelerinde her
     kaydın kalıcı bir kimliği var; model güncel taslağı görür ve aynı kaydı
     o kimlikle döndürür.
  3. Hızlı katmanda, arızada yedek modele düşen LLM zinciri (app/core/llm.py).

Ajana özel olan her şey (`AjanTanimi`) dışarıdan verilir: açılış sorusu,
sistem talimatı, çıkarım şeması, zorunlu alanlar. Bir ajanın kendine has bir
dalı varsa (Keşif'in "hiç projem yok" fallback zinciri gibi) `oncelikli_dal`
ya da `ek_dal` ile eklenir — motorun içinde ajana özel dal yok.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.core.llm import HizSinirHatasi, llm_hatasini_cevir, yedekli_zincir
from app.core.metin import sade_anahtar

__all__ = ["HizSinirHatasi"]

# Kısa tavan (agent-specs.md § 1.2): ajana özel ek soruların varsayılan tavanı
# (Keşif kendi tavanını `maks_ek_turu` ile veriyor); Tanımlama zorunlu alanları
# için de bu tavanı kullanır.
MAKS_TAKIP_TURU = 2
# Zorunlu alanlar için ayrı ve daha yüksek bir tavan: eksik alanla kart
# kapatmak, sohbeti bir tur uzatmaktan kötü (boş "sektör ilgisi" eşleştirmede
# doğrudan skora yansıyor). Yine de sonsuz döngü olmasın diye bir sınır var;
# tavana gelinirse taslak kapanır, boş alanı ajanın `tamamla`sı ya da
# kullanıcı taslak ekranında tamamlar.
MAKS_ZORUNLU_TURU = 6
# Kullanıcı aynı soru için en fazla bu kadar açıklama alır; sonra sohbet
# ilerler. Sınır yoksa "anlamadım" diyen biri aynı soruda takılı kalabilir.
MAKS_ACIKLAMA = 2

# Nesne listelerindeki her kaydın kalıcı kimliği (ör. "c1"). Model bir kaydın
# başlığını her turda farklı yazabiliyor; kayıt başlıkla değil bununla bulunur.
KIMLIK = "kimlik"

TASLAK_BASLIGI = (
    "ŞU ANA KADARKİ TASLAK (sohbetten çıkardıkların; bu turda yeni bilgiyle "
    "tamamla, zaten olan bir kaydı güncellerken onun kimliğini kullan; kullanıcı "
    "bir alanı daha açık ya da farklı anlattıysa yeni hâlini yaz):\n"
)


class SohbetDurumu(TypedDict, total=False):
    """Her ajanın paylaştığı durum. Ajanlar bunu genişletebilir."""

    mesajlar: Annotated[list[AnyMessage], add_messages]
    taslak: dict[str, Any]
    # Sohbeti açan hesap (Faz B). Sonraki cevap ve onay istekleri token'daki
    # hesapla karşılaştırılır; başkasının sohbeti 404 (app/api/sahiplik.py).
    sahip_hesap_id: str
    # Zorunlu alan takip turları
    takip_turu: int
    # Ajana özel ek sorular (Keşif'te çıktı başına ölçüt/rol) AYRI sayılır:
    # eskiden aynı sayacı paylaşıyorlardı ve zorunlu alanlar 2 tur sürünce
    # ek sorular hiç sorulmuyordu.
    ek_takip_turu: int
    # Sorulmuş ek soruların anahtarları. Kullanıcı "bilmiyorum" deyince alan
    # boş kalıyor; bu liste olmadan aynı soru kelimesi kelimesine tekrar
    # geliyordu. Her ek soru en fazla bir kez sorulur.
    sorulan_ekler: list[str]
    # Kullanıcıya gösterilen son metin (API'nin `soru` alanı). Açıklama
    # turunda açıklamalı yeni ifade; `bekleyen_soru` ise sorunun kendisi.
    # Akış bekleyen soruya bakar, gösterilen metne değil: model soruyu başka
    # sözcüklerle sorsa da sohbet kaymaz.
    sonraki_soru: str | None
    bekleyen_soru: str | None
    # Bekleyen soru için şimdiye kadar yapılan açıklama sayısı (MAKS_ACIKLAMA)
    aciklama_sayisi: int
    taslak_hazir: bool
    # Son turun çıkarımından karar düğümüne taşınan takip sorusu önerisi
    son_takip_sorusu: str | None
    # O sorunun hangi alanı hedeflediği (modelin kendi etiketi, çıkarım
    # şemasındaki `takip_konusu`). Karar düğümü soruyu yalnızca konusu eksik
    # bir zorunlu alansa kullanır — bkz. `zorunlu_alan_sorusu`.
    son_takip_konusu: str | None
    # Son turda kullanıcı soruyu cevaplamak yerine açıklama istedi mi, modelin
    # yazdığı açıklama ve bu turda taslağa yeni bilgi girip girmediği.
    son_aciklama_istedi: bool
    son_aciklama: str | None
    # Son turda kullanıcı soruyu bilmediğini ya da yanıtlayamayacağını söyledi
    # mi. Açıklama isteğiyle karışıyordu: "bilmiyorum" diyen firmaya açıklama
    # turu açılıyor, açıklama tur hakkından düşmediği için sohbet uzuyordu.
    son_cevap_veremiyor: bool
    taslak_degisti: bool
    # Sohbetin başında bilinen, SORULMAYACAK bilgiler (Keşif'te kayıt formunun
    # profil alanları). Çıkarımda sistem talimatının ardından ayrı bir sistem
    # mesajı olarak gider; boşsa hiç gitmez (docs/plans/genc-akisi.md § 5.3).
    profil_baglami: str | None
    # İhtiyaç sohbetinde ilanın kimi aradığı (genc | firma); hangi soru setinin
    # (grafik) devam edeceğini belirler (docs/plans/firma-akisi.md § 5).
    aranan: str | None


class SohbetCikarimi(BaseModel):
    """Her sohbet ajanının çıkarım şemasının tabanı: açıklama isteği.

    Sahada görüldü: genç "örnek verir misin?" dedi, sistem cevaptan yeni bir
    alan çıkmadığı için sıradaki soruya geçti. Açıklama isteği ayrı bir
    bilgi olarak alınır; karar düğümü aynı soruyu açıklamayla yeniden sorar.
    """

    aciklama_istedi: bool = Field(
        default=False,
        description=(
            "Kullanıcı bu turda son soruyu cevaplamak yerine açıklama ya da örnek "
            "istediyse True ('örnek verir misin', 'anlamadım', 'ne demek istiyorsun')."
        ),
    )
    aciklama: str | None = Field(
        default=None,
        description=(
            "aciklama_istedi True ise kullanıcıya gidecek mesajın tamamı: son soruyu, "
            "kullanıcının anlattıklarına uyan kısa bir örnekle açıklayan 1-2 cümle, "
            "ardından AYNI soruyu kısaca yeniden sor. Başka bir konuya geçme; önceki "
            "mesajdaki övgü ya da giriş cümlesini tekrarlama."
        ),
    )
    cevap_veremiyor: bool = Field(
        default=False,
        description=(
            "Kullanıcı son soruyu bilmediğini, ölçmediğini ya da yanıtlayamayacağını "
            "söylediyse True ('bilmiyorum', 'emin değilim', 'ölçmüyoruz'). Bu bir "
            "açıklama isteği DEĞİLDİR; bu durumda aciklama_istedi False kalır."
        ),
    )


@dataclass(frozen=True)
class NesneListesi:
    """Taslakta nesnelerden oluşan bir liste alanı (örn. Keşif'in çalışmaları)."""

    alan: str
    # Kimliksiz gelen kaydın yedek eşleştirme anahtarı (örn. "baslik")
    anahtar: str
    # Kalıcı kimliklerin öneki: "c" → c1, c2…
    kimlik_oneki: str


@dataclass(frozen=True)
class AjanTanimi:
    """Bir sohbet ajanının motora verdiği her şey."""

    ad: str
    acilis_sorusu: str
    sistem_talimati: str
    cikarim_semasi: type[SohbetCikarimi]
    # Model açıklama istendiğini söyleyip açıklama yazmazsa kullanılan metin.
    # Ajana göre hitap değişiyor (gence "sen", firmaya "siz").
    aciklama_yedegi: str
    # Üzerine yazılan alanlar (tek değer) ve tekrarsız eklenen liste alanları
    skaler_alanlar: tuple[str, ...] = ()
    liste_alanlari: tuple[str, ...] = ()
    nesne_listeleri: tuple[NesneListesi, ...] = ()
    # Tek nesneden oluşan alanlar (Tanımlama'da başarı ölçütü): alan alan
    # birleşir, dolu yeni değer eskisinin yerine geçer, boş gelen silmez.
    nesne_alanlari: tuple[str, ...] = ()
    zorunlu_alanlar: tuple[str, ...] = ()
    # Zorunlu alan eksikken kaç tur soru sorulabilir (ajana göre değişir).
    maks_zorunlu_turu: int = MAKS_ZORUNLU_TURU
    # Ajana özel ek sorular en fazla kaç tur (kendi sayacıyla).
    maks_ek_turu: int = MAKS_TAKIP_TURU
    # Ajana özel eksikler: (anahtar, soru) listesi. Zorunlu alanlar
    # tamamlandıktan SONRA sorulur — örn. Keşif'te her çıktının sayısal
    # sonucu ve kullanıcının kendi payı.
    ek_eksikler: Callable[[dict[str, Any]], list[tuple[str, str]]] | None = None
    # LLM takip sorusu üretmezse kullanılan sabit metinler
    yedek_sorular: Mapping[str, str] = field(default_factory=dict)
    # Ajana özel dallar. Bir durum güncellemesi dönerse sohbet o soruyla devam
    # eder, None dönerse karar sıradaki adıma geçer. `oncelikli_dal` zorunlu
    # alanlardan ÖNCE, `ek_dal` takip soruları bittikten SONRA çalışır (Keşif'te
    # "hiç projem yok" diyen gence okul ödevi soruları hemen, söylemeyene sonda).
    oncelikli_dal: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None
    ek_dal: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None
    # Çıkarımdan taslağa değil, doğrudan duruma yazılacak bayraklar (Keşif'te
    # "kullanıcı projesi olmadığını söyledi"). Önceki durumu da görür ki bir
    # kez söylenen şey sonraki turda kaybolmasın.
    ek_cikarim_alanlari: Callable[[SohbetCikarimi, Mapping[str, Any]], dict[str, Any]] | None = None
    # Her çıkarımdan sonra taslağa uygulanan ajan kuralı; güncel durumu görür
    # (Keşif'te çalışması olmadığını söyleyen gencin deneyimi "potansiyel").
    taslak_kurali: Callable[[dict[str, Any], Mapping[str, Any]], dict[str, Any]] | None = None
    # Taslağı kapatmadan önceki son rötuş (örn. "potansiyel" etiketi)
    tamamla: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def cikarim_zinciri(sema: type[BaseModel], is_adi: str) -> Runnable:
    """Hızlı katmanda, aynı prompt ve şemayla çalışan iki modelden oluşan zincir.

    Yapılandırılmış çıkarım ince akıl yürütme istemiyor; hızlı katman yeterli
    (app/core/llm.py). Ana model arıza ya da hız sınırı verirse aynı çağrı
    yedek modele düşer. Yedek de başarısız olursa hata çağırana kadar çıkar —
    sohbet checkpointer'da durduğu için kaybolmaz, kullanıcı tekrar deneyebilir.

    Önbellek ajanın kendi sarmalayıcısında (her ajan kendi zincirini tutar).
    """
    return yedekli_zincir("hizli", is_adi, lambda m: m.with_structured_output(sema))


def bos_taslak(tanim: AjanTanimi) -> dict[str, Any]:
    taslak: dict[str, Any] = {alan: None for alan in tanim.skaler_alanlar}
    for alan in tanim.liste_alanlari:
        taslak[alan] = []
    for liste in tanim.nesne_listeleri:
        taslak[liste.alan] = []
    for alan in tanim.nesne_alanlari:
        taslak[alan] = None
    return taslak


def eksik_alanlar(tanim: AjanTanimi, taslak: dict[str, Any]) -> list[str]:
    return [alan for alan in tanim.zorunlu_alanlar if not taslak.get(alan)]


def _yeni_kimlik(nesneler: Sequence[dict[str, Any]], onek: str) -> str:
    """Kullanılmamış ilk kimlik: c1, c2…"""
    kullanilan = {nesne.get(KIMLIK) for nesne in nesneler}
    sira = 1
    while f"{onek}{sira}" in kullanilan:
        sira += 1
    return f"{onek}{sira}"


def _kimlikli_kopya(nesneler: Sequence[dict[str, Any]], onek: str) -> list[dict[str, Any]]:
    """Kayıtların kopyası; kimliği olmayana (bu özellikten önceki taslak) kimlik verir."""
    kopyalar = [dict(nesne) for nesne in nesneler]
    for kopya in kopyalar:
        if not kopya.get(KIMLIK):
            kopya[KIMLIK] = _yeni_kimlik(kopyalar, onek)
    return kopyalar


def _nesneleri_birlestir(
    nesneler: Sequence[dict[str, Any]], gelenler: Sequence[Any], liste: NesneListesi
) -> list[dict[str, Any]]:
    """Aynı işi anlatan kayıtları tek kayıtta toplar.

    Kayıt önce kimliğiyle bulunur: model taslağı görüyor ve bildiği bir kaydı
    kimliğiyle döndürüyor. Başlığa güvenmek yetmiyordu, model aynı işi her
    turda başka adla yazabiliyor ("Kütüphane sistemi" / "Mahalle kütüphanesi
    takip uygulaması") ve kart aynı işi iki kez taşıyordu.

    Eşleşmenin türü birleştirme kuralını seçer:
      - Kimlikle: model taslağı görerek güncel anlayışını döndürüyor; dolu
        yeni değer eskisinin yerine geçer (`_kaydi_guncelle`). Sahada görüldü:
        ilk turdaki belirsiz "arkadaşımla yaptık" payı korunuyor, sonraki
        turdaki "backend'i ben yazdım" yazılamıyordu.
      - Başlıkla (kimliksiz kayıt): noktalama ve büyük/küçük harf farkı yok
        sayılır ("Team To Do" / "Team ToDo"); modelin hangi kaydı kastettiği
        kesin olmadığı için yalnızca BOŞ alanlar dolar (`_bos_alanlari_doldur`).

    Hiçbir kayıt silinmez: model bir turda bir kaydı unutursa veri kaybolmaz.
    """
    sonuc = _kimlikli_kopya(nesneler, liste.kimlik_oneki)
    kimlikle = {nesne[KIMLIK]: nesne for nesne in sonuc}
    anahtarla = {sade_anahtar(nesne[liste.anahtar]): nesne for nesne in sonuc}

    for gelen in gelenler:
        veri = gelen.model_dump()
        kimlik = veri.pop(KIMLIK, None)
        anahtar = sade_anahtar(veri[liste.anahtar])
        if kimlik in kimlikle:
            _kaydi_guncelle(kimlikle[kimlik], veri, korunan=liste.anahtar)
        elif anahtar in anahtarla:
            _bos_alanlari_doldur(anahtarla[anahtar], veri)
        else:
            yeni = {KIMLIK: _yeni_kimlik(sonuc, liste.kimlik_oneki), **veri}
            sonuc.append(yeni)
            kimlikle[yeni[KIMLIK]] = yeni
            anahtarla[anahtar] = yeni

    return sonuc


def _kaydi_guncelle(mevcut: dict[str, Any], veri: Mapping[str, Any], *, korunan: str) -> None:
    """Dolu yeni değerler eskisinin yerine geçer; boş gelen alan eskisini silmez.

    `korunan` alan (başlık) değişmez: kullanıcı onu taslak ekranında düzeltir,
    modelin her turda yeniden adlandırması kartı oynatmasın.
    """
    for alan_adi, deger in veri.items():
        if deger and alan_adi != korunan:
            mevcut[alan_adi] = deger


def _bos_alanlari_doldur(mevcut: dict[str, Any], veri: Mapping[str, Any]) -> None:
    """Yalnızca boş alanlar dolar; ilk anlatılan korunur."""
    for alan_adi, deger in veri.items():
        if deger and not mevcut.get(alan_adi):
            mevcut[alan_adi] = deger


def birlestir(tanim: AjanTanimi, taslak: dict[str, Any], cikarim: BaseModel) -> dict[str, Any]:
    """Yeni çıkarımı mevcut taslağa ekler — boş gelen alan eskisini silmez."""
    yeni = dict(taslak)

    for alan in tanim.skaler_alanlar:
        deger = getattr(cikarim, alan, None)
        if deger:
            yeni[alan] = deger

    for alan in tanim.liste_alanlari:
        mevcut = list(yeni.get(alan) or [])
        for deger in getattr(cikarim, alan, []) or []:
            if deger and deger not in mevcut:
                mevcut.append(deger)
        yeni[alan] = mevcut

    for liste in tanim.nesne_listeleri:
        yeni[liste.alan] = _nesneleri_birlestir(
            yeni.get(liste.alan) or [], getattr(cikarim, liste.alan, []) or [], liste
        )

    for alan in tanim.nesne_alanlari:
        gelen = getattr(cikarim, alan, None)
        if gelen is not None:
            nesne = dict(yeni.get(alan) or {})
            _kaydi_guncelle(nesne, gelen.model_dump(), korunan="")
            yeni[alan] = nesne

    return yeni


def taslak_baglami(taslak: Mapping[str, Any] | None) -> str | None:
    """Şu ana kadarki taslak, modele ayrı bir sistem mesajı olarak (saf).

    Model önceki turlarda ne çıkardığını görmezse aynı kaydı her turda yeniden
    adlandırıyor ve kimliğini bilemiyor. Boş taslakta None: mesaj gitmez.
    """
    if not taslak or not any(taslak.values()):
        return None
    return TASLAK_BASLIGI + json.dumps(taslak, ensure_ascii=False)


def istem_mesajlari(tanim: AjanTanimi, durum: Mapping[str, Any]) -> list[AnyMessage]:
    """Çıkarım çağrısının mesajları: talimat, varsa profil ve taslak, sonra sohbet."""
    baglamlar = (
        tanim.sistem_talimati,
        durum.get("profil_baglami"),
        taslak_baglami(durum.get("taslak")),
    )
    return [
        *(SystemMessage(content=baglam) for baglam in baglamlar if baglam),
        *durum["mesajlar"],
    ]


# --- Grafik düğümleri ------------------------------------------------------


def _acilis_dugumu(tanim: AjanTanimi, ek_baslangic: Mapping[str, Any]):
    async def acilis(durum: dict[str, Any]) -> dict[str, Any]:
        """Sohbeti açar. LLM çağrısı yok — açılış sorusu sabit."""
        return soru_durumu(
            tanim.acilis_sorusu,
            taslak=bos_taslak(tanim),
            takip_turu=0,
            ek_takip_turu=0,
            sorulan_ekler=[],
            **ek_baslangic,
        )

    return acilis


def _cikar_dugumu(tanim: AjanTanimi, zincir_uret: Callable[[], Runnable]):
    async def cikar(durum: dict[str, Any]) -> dict[str, Any]:
        """Konuşmanın tamamını yapılandırılmış alanlara döker (function calling)."""
        try:
            cikarim = await zincir_uret().ainvoke(istem_mesajlari(tanim, durum))
        except Exception as hata:
            # Sağlayıcı anlık hız sınırı (429) ya da 5xx/zaman aşımı
            # verebiliyor. İkisini de 500 olarak değil, ne olduğunu söyleyen
            # ayrı hatalar olarak taşı.
            cevrilmis = llm_hatasini_cevir(hata)
            raise cevrilmis from hata

        bayraklar = tanim.ek_cikarim_alanlari(cikarim, durum) if tanim.ek_cikarim_alanlari else {}
        onceki = durum.get("taslak") or bos_taslak(tanim)
        taslak = birlestir(tanim, onceki, cikarim)
        if tanim.taslak_kurali is not None:
            taslak = tanim.taslak_kurali(taslak, {**durum, **bayraklar})
        return {
            "taslak": taslak,
            "taslak_degisti": taslak != onceki,
            "son_takip_sorusu": getattr(cikarim, "takip_sorusu", None),
            "son_takip_konusu": getattr(cikarim, "takip_konusu", None),
            "son_aciklama_istedi": cikarim.aciklama_istedi,
            "son_aciklama": cikarim.aciklama,
            "son_cevap_veremiyor": cikarim.cevap_veremiyor,
            **bayraklar,
        }

    return cikar


def soru_durumu(soru: str, **guncellemeler: Any) -> dict[str, Any]:
    """Kullanıcıya yeni bir soru: gösterilen metin ve bekleyen soru aynı,
    açıklama sayacı sıfırdan başlar. Sayaç gibi ek alanlar `guncellemeler`le."""
    return {
        "mesajlar": [AIMessage(content=soru)],
        "sonraki_soru": soru,
        "bekleyen_soru": soru,
        "aciklama_sayisi": 0,
        "taslak_hazir": False,
        **guncellemeler,
    }


def aciklama_gerekli(durum: Mapping[str, Any]) -> bool:
    """Bekleyen soru açıklamayla yeniden sorulmalı mı?

    Kullanıcı açıklama istediyse ve bu turda taslağa yeni bilgi girmediyse.
    "Bilmiyorum" açıklama isteği değildir: model ikisini birden işaretlese de
    soru akışı (sayaçlı) ilerler, açıklama turu açılmaz.
    Hem soru sorup hem cevap veren kullanıcıda (taslak değişti) sohbet normal
    ilerler; aynı soru boşuna tekrarlanmaz. Soru başına en fazla MAKS_ACIKLAMA.
    """
    return (
        bool(durum.get("son_aciklama_istedi"))
        and not durum.get("son_cevap_veremiyor")
        and not durum.get("taslak_degisti")
        and bool(_bekleyen_soru(durum))
        and durum.get("aciklama_sayisi", 0) < MAKS_ACIKLAMA
    )


def _bekleyen_soru(durum: Mapping[str, Any]) -> str | None:
    # Bu alandan önce açılmış sohbette yalnızca `sonraki_soru` var.
    return durum.get("bekleyen_soru") or durum.get("sonraki_soru")


def aciklama_durumu(tanim: AjanTanimi, durum: Mapping[str, Any]) -> dict[str, Any]:
    """Açıklama ve aynı soru. Hiçbir soru sayacına dokunmaz: açıklama turu
    tur hakkından düşmez, sorulmuş ek soru listesi değişmez."""
    metin = aciklama_metni(tanim, durum)
    return {
        "mesajlar": [AIMessage(content=metin)],
        "sonraki_soru": metin,
        "aciklama_sayisi": durum.get("aciklama_sayisi", 0) + 1,
        "taslak_hazir": False,
    }


def aciklama_metni(tanim: AjanTanimi, durum: Mapping[str, Any]) -> str:
    """Açıklama turunda kullanıcıya gidecek metin.

    Modelin açıklaması soruyu kendi içinde yeniden soruyor (şemadaki kural);
    kod bir şey eklemez. Eskiden bekleyen soru kelimesi kelimesine sona
    ekleniyordu: soru "Harika bir çalışma olmuş." diye başladığında övgü de
    ikinci kez geliyordu. Model açıklama yazmadıysa ajanın yedek cümlesi ve
    bekleyen soru gider: kullanıcı hiçbir zaman sorusuz kalmaz.
    """
    if aciklama := durum.get("son_aciklama"):
        return aciklama
    return f"{tanim.aciklama_yedegi}\n\n{_bekleyen_soru(durum)}"


def zorunlu_alan_sorusu(tanim: AjanTanimi, durum: dict[str, Any], eksikler: list[str]) -> str:
    """Zorunlu alan eksikken sorulacak soru.

    Modelin önerdiği soru yalnızca konusu eksik bir zorunlu alansa kullanılır;
    değilse ilk eksik alanın sabit sorusu sorulur.

    Neden: sistem talimatı modele "her çıktının ölçülebilir sonucunu ve kişinin
    kendi payını da öğren" diyor. Model zorunlu fazda sektör eksikken
    "projede rolün neydi" diye sordu; bu soru ne zorunlu alanı doldurdu ne de
    sistemin "sorulan ek sorular" defterine girdi. Bir sonraki turda sistemin
    ek sorusu aynı konuyu yeniden sordu. Zorunlu faz artık yalnızca zorunlu
    alanları soruyor; rol/ölçüt konusunu tek başına ek faz yönetiyor.
    """
    onerilen = durum.get("son_takip_sorusu")
    if onerilen and durum.get("son_takip_konusu") in eksikler:
        return onerilen
    return tanim.yedek_sorular[eksikler[0]]


async def karar(tanim: AjanTanimi, durum: dict[str, Any]) -> dict[str, Any]:
    """Takip sorusu mu, ajana özel dal mı, yoksa taslak mı — tek karar noktası."""
    # 0) Kullanıcı soruyu anlamadıysa sıradaki soruya geçilmez: aynı soru
    #    açıklamayla yeniden sorulur.
    if aciklama_gerekli(durum):
        return aciklama_durumu(tanim, durum)

    # 0b) Ajanın zorunlu alanlardan önce gelen dalı.
    if tanim.oncelikli_dal is not None:
        oncelikli = tanim.oncelikli_dal(durum)
        if oncelikli is not None:
            return oncelikli

    taslak = durum["taslak"]
    eksikler = eksik_alanlar(tanim, taslak)
    takip_turu = durum.get("takip_turu", 0)

    # 1) Zorunlu alan eksikse sormaya devam et. Kartı eksik kapatmak son
    #    çare; tavan yalnızca sonsuz döngüyü engelliyor.
    if eksikler and takip_turu < tanim.maks_zorunlu_turu:
        soru = zorunlu_alan_sorusu(tanim, durum, eksikler)
        return soru_durumu(soru, takip_turu=takip_turu + 1)

    # 2) Ajana özel eksikler (Keşif'te çıktı başına ölçülebilir sonuç ve rol).
    #    Zorunlu alanlardan sonra, kendi sayacıyla ve daha kısa bir tavanla
    #    soruluyor: bunlar kartı güçlendirir ama olmadan da kart kurulabilir.
    #    Sorulmuş bir soru bir daha sorulmaz — kullanıcı bilmiyorsa ısrar yok,
    #    sıradaki eksiğe geçilir.
    ek_takip_turu = durum.get("ek_takip_turu", 0)
    if tanim.ek_eksikler is not None and ek_takip_turu < tanim.maks_ek_turu:
        sorulanlar = list(durum.get("sorulan_ekler") or [])
        sorulmamislar = [
            (anahtar, soru)
            for anahtar, soru in tanim.ek_eksikler(taslak)
            if anahtar not in sorulanlar
        ]
        if sorulmamislar:
            anahtar, soru = sorulmamislar[0]
            return soru_durumu(
                soru, ek_takip_turu=ek_takip_turu + 1, sorulan_ekler=[*sorulanlar, anahtar]
            )

    # 3) Ajana özel dal (Keşif'te "hiç projem yok" zinciri; Tanımlama'da yok).
    if tanim.ek_dal is not None:
        ek = tanim.ek_dal(durum)
        if ek is not None:
            return ek

    # 4) Taslak hazır.
    son_taslak = tanim.tamamla(taslak) if tanim.tamamla else dict(taslak)
    return {"taslak": son_taslak, "sonraki_soru": None, "taslak_hazir": True}


def _karar_dugumu(tanim: AjanTanimi):
    async def karar_dugumu(durum: dict[str, Any]) -> dict[str, Any]:
        return await karar(tanim, durum)

    return karar_dugumu


def _baslangic_yonu(durum: dict[str, Any]) -> Literal["acilis", "cikar"]:
    """İlk çağrıda açılış sorusu, sonrakilerde çıkarım."""
    return "cikar" if durum.get("mesajlar") and durum.get("taslak") is not None else "acilis"


def grafik_derle(
    tanim: AjanTanimi,
    durum_semasi: type,
    checkpointer: BaseCheckpointSaver,
    zincir_uret: Callable[[], Runnable],
    ek_baslangic: Mapping[str, Any] | None = None,
):
    """Ajanın grafiğini derler. Checkpointer uygulama ömrü boyunca paylaşılır."""
    grafik = StateGraph(durum_semasi)
    grafik.add_node("acilis", _acilis_dugumu(tanim, ek_baslangic or {}))
    grafik.add_node("cikar", _cikar_dugumu(tanim, zincir_uret))
    grafik.add_node("karar", _karar_dugumu(tanim))

    grafik.add_conditional_edges(START, _baslangic_yonu, {"acilis": "acilis", "cikar": "cikar"})
    grafik.add_edge("acilis", END)
    grafik.add_edge("cikar", "karar")
    grafik.add_edge("karar", END)

    return grafik.compile(checkpointer=checkpointer)


def kullanici_mesaji(metin: str) -> HumanMessage:
    return HumanMessage(content=metin)
