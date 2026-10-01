"""Vaka şeması ve yükleyici.

Bir vaka: gencin iddiası, kanıt parçaları, referans yanıtları, kimlik bilgisi ve
**beklenen** güven göstergesi. Etiketin anlamı `ETIKETLEME_REHBERI.md`'de.

Şema hedef sistemin girdilerini taşır (bağlı hesap, dosya, 4 soruluk referans);
bugünkü sistem bunların bir kısmını kullanmaz. Vaka bir kez yazılır, her
sistem sürümü aynı vakayla ölçülür.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SETI_KLASORU = Path(__file__).resolve().parent.parent / "tests" / "degerlendirme_seti"
VAKA_KLASORU = SETI_KLASORU / "vakalar"

BASLIKLAR: tuple[str, ...] = ("kanit", "sonuc", "rol", "referans")


class Alan(StrEnum):
    """Meslek alanları (plan § 8). Adalet ölçümü bu kırılımla yapılır."""

    YAZILIM = "yazilim"
    TASARIM = "tasarim"
    YAZI = "yazi"
    MEDYA = "medya"
    VERI = "veri"
    AKADEMIK = "akademik"
    MUHENDISLIK = "muhendislik"
    YARISMA = "yarisma"
    SERTIFIKA = "sertifika"
    STAJ_IS = "staj_is"
    GONULLULUK = "gonulluluk"
    PAZARLAMA = "pazarlama"
    # Satış, operasyon, İK, finans, hukuk, sağlık: kamuya açık çıktısı olmayan işler.
    KAMUYA_KAPALI = "kamuya_kapali"


class _Kati(BaseModel):
    """Vaka dosyalarında yazım hatası sessizce yutulmasın: bilinmeyen alan hatadır."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Iddia(_Kati):
    baslik: str
    aciklama: str | None = None
    olculebilir_sonuc: str | None = None
    kendi_rolu: str | None = None
    is_turu: str | None = None


class KanitGirdisi(_Kati):
    tur: Literal["link", "dosya", "gorsel"]
    url: str | None = None
    # `tests/degerlendirme_seti/dosyalar/` altına göre yol
    dosya: str | None = None

    @model_validator(mode="after")
    def _tur_ile_tutarli(self) -> KanitGirdisi:
        if self.tur == "link" and not self.url:
            raise ValueError("link kanıtının url'i olmalı")
        if self.tur != "link" and not self.dosya:
            raise ValueError("dosya / görsel kanıtının dosya yolu olmalı")
        return self


Yanit = Literal["evet", "kismen", "hayir", "bilmiyorum"]


class ReferansGirdisi(_Kati):
    eposta: str
    iliski: Literal["yonetici", "takim_arkadasi", "ogretmen", "musteri", "diger"]
    yanitladi: bool = True
    iddia_dogru: Yanit | None = None
    pay_dogru: Yanit | None = None
    sonuc_dogru: Yanit | None = None


class BagliHesap(_Kati):
    saglayici: str
    kullanici_adi: str
    yontem: Literal["oauth", "profil_kodu"]


class Kimlik(_Kati):
    ad: str
    eposta: str
    eposta_dogrulandi: bool = False
    bagli_hesaplar: tuple[BagliHesap, ...] = ()


# Bir başlığın beklentisi: tek değer, "—" (None) ya da kabul edilebilir değerler listesi.
BaslikBeklentisi = int | None | list[int | None]


class Beklenen(_Kati):
    kanit: BaslikBeklentisi
    sonuc: BaslikBeklentisi
    rol: BaslikBeklentisi
    referans: BaslikBeklentisi

    @field_validator("kanit", "sonuc", "rol", "referans")
    @classmethod
    def _aralik(cls, deger: BaslikBeklentisi) -> BaslikBeklentisi:
        degerler = deger if isinstance(deger, list) else [deger]
        if not degerler:
            raise ValueError("kabul listesi boş olamaz")
        for d in degerler:
            if d is not None and not 0 <= d <= 3:
                raise ValueError(f"başlık değeri 0-3 ya da null olmalı: {d}")
        return deger

    def baslik(self, ad: str) -> BaslikBeklentisi:
        return getattr(self, ad)


class Vaka(_Kati):
    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    alan: Alan
    # Bu vaka neyi sınıyor? (etiketleyene ve karneyi okuyana)
    amac: str
    kotu_niyetli: bool = False
    bireysel: bool = False
    iddia: Iddia
    kart_yetenekleri: tuple[str, ...] = ()
    kanitlar: tuple[KanitGirdisi, ...] = ()
    referanslar: tuple[ReferansGirdisi, ...] = ()
    kimlik: Kimlik
    # Etiket (Zühre); `etiketleyen` olmadan geçersiz.
    beklenen: Beklenen | None = None
    # Öneri (etiket değil): yalnızca "taslak etiket" karnesinde kullanılır.
    onerilen: Beklenen | None = None
    etiketleyen: str | None = None
    gozden_geciren: str | None = None
    notlar: str | None = None

    @model_validator(mode="after")
    def _etiket_sahipli(self) -> Vaka:
        if self.beklenen is not None and not self.etiketleyen:
            raise ValueError(f"{self.id}: etiketin etiketleyeni yok")
        return self

    @property
    def etiketli(self) -> bool:
        return self.beklenen is not None

    def etiket(self, taslak: bool) -> Beklenen | None:
        """Karnede kullanılacak beklenti: etiket; taslak karnede etiket yoksa öneri."""
        if self.beklenen is not None:
            return self.beklenen
        return self.onerilen if taslak else None

    @property
    def linkler(self) -> tuple[str, ...]:
        return tuple(k.url for k in self.kanitlar if k.tur == "link" and k.url)


class VakaDosyasiHatasi(ValueError):
    pass


def vakalari_yukle(klasor: Path = VAKA_KLASORU) -> list[Vaka]:
    """Klasördeki bütün `*.yaml` dosyalarını okur; kimlikler tekil olmalı."""
    vakalar: list[Vaka] = []
    for yol in sorted(klasor.glob("*.yaml")):
        icerik = yaml.safe_load(yol.read_text(encoding="utf-8")) or []
        if not isinstance(icerik, list):
            raise VakaDosyasiHatasi(f"{yol.name}: dosya bir vaka listesi olmalı")
        for ham in icerik:
            try:
                vakalar.append(Vaka.model_validate(ham))
            except ValueError as hata:
                raise VakaDosyasiHatasi(f"{yol.name}: {hata}") from hata

    gorulen: set[str] = set()
    for vaka in vakalar:
        if vaka.id in gorulen:
            raise VakaDosyasiHatasi(f"tekrarlanan vaka kimliği: {vaka.id}")
        gorulen.add(vaka.id)
    return vakalar
