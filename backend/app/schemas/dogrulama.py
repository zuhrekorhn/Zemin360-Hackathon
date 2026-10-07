"""Doğrulama Ajanı uç noktalarının şemaları (docs/api-contracts.md § Doğrulama)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.core.kanit_okuma.adres import KANIT_LINKI_UZUNLUGU

# Referans formu (docs/dogrulama.md § 7); değer kümeleri app/agents/dogrulama/kurallar.py ile aynı.
Iliski = Literal["yonetici", "takim_arkadasi", "ogretmen_danisman", "musteri", "diger"]
FormCevabi = Literal["evet", "kismen", "hayir", "bilmiyorum"]

KanitLinki = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=KANIT_LINKI_UZUNLUGU)
]


class KanitLinkiIstegi(BaseModel):
    """Çalışmaya link parçası ekler (POST /dogrulama/kalem/{id}/kanit)."""

    model_config = ConfigDict(extra="forbid")

    url: KanitLinki


class ReferansIstegiGirdisi(BaseModel):
    """Çalışma için referans ister (POST /dogrulama/kalem/{id}/referans). Model çağrılmaz."""

    model_config = ConfigDict(extra="forbid")

    referans_email: EmailStr


class KanitParcasiYaniti(BaseModel):
    """Bir kanıt parçası: link, dosya ya da görsel. Dosyanın kendisi dönmez; indirme
    adresi ayrı uçtan, kısa ömürlü (GET .../kanit/{id}/indir)."""

    id: uuid.UUID
    tur: str
    url: str | None
    platform: str | None = None
    erisim: str | None = None
    seviye: str | None = None
    dosya_adi: str | None = None
    dosya_boyutu: int | None = None
    gorunur_firmaya: bool = False
    # e-Devlet belgesinin GİRVAK incelemesi: bekliyor | onaylandi | reddedildi
    girvak_incelemesi: str | None = None
    # Görselin C2PA bilgisindeki üretim aracı (ör. "Adobe Photoshop 25.0")
    uretim_araci: str | None = None

    model_config = {"from_attributes": True}


class DosyaGorunurlukIstegi(BaseModel):
    """Genç dosyanın firmalara görünüp görünmeyeceğini seçer (PATCH .../kanit/{id})."""

    model_config = ConfigDict(extra="forbid")

    gorunur_firmaya: bool


class IndirmeAdresiYaniti(BaseModel):
    adres: str


class GuvenSkoruYaniti(BaseModel):
    """Dört bileşen ayrı ayrı gösterilir — tek sayıya indirilmez.

    docs/agent-specs.md § 4: "her biri 0-3 puan, tek sayıya indirilmez".
    null = "—": başlık değerlendirilmedi ya da yanıt yok; 0 ile karıştırılmaz.
    """

    kanit_orijinalligi: int | None
    sonuc_olculebilirligi: int | None
    rol_netligi: int | None
    ucuncu_taraf_onayi: int | None
    gerekce_metni: str | None

    model_config = {"from_attributes": True}


class ReferansDurumuYaniti(BaseModel):
    """Gencin (ve GİRVAK'ın) gördüğü referans satırı. Token ve yanıt linki yok:
    e-posta referansa doğrudan gider."""

    id: uuid.UUID
    referans_email: str
    # "bekliyor" | "yanitlandi" | "yanit_yok" | "geri_cekildi"
    durum: str
    # Eski formun 1-5 puanı; yeni yanıtlarda null.
    puan: int | None
    iliski: str | None = None
    iddia_dogru: str | None = None
    pay_dogru: str | None = None
    sonuc_dogru: str | None = None
    yanit_metni: str | None
    olusturma_tarihi: dt.datetime
    # Güç işareti (puan değil): "kurumsal_eposta" | "egitim_eposta" | null
    guc: str | None = None
    # False: yanıt iş kaleminin önceki hâli için verildi; geçmiş olarak görünür,
    # güven göstergesine girmez (docs/kararlar.md G8). Genç yeniden isteyebilir.
    guncel: bool = True
    # "Referansı yeniden iste" düğmesi; kural backend'de tek yerde
    # (referans_yeniden_istenebilir_mi), arayüz tekrar etmez.
    yeniden_istenebilir: bool = False
    # "Geri çek" düğmesi (yalnızca bekleyen istek).
    geri_cekilebilir: bool = False


class ReferansYenidenIsteIstegi(BaseModel):
    referans_id: uuid.UUID


class KanitDurumuYaniti(BaseModel):
    somut_cikti_id: uuid.UUID
    baslik: str
    kanitlar: list[KanitParcasiYaniti]
    # Bu istekte okunan linkin açılıp açılmadığı; okuma yapılmadıysa None.
    link_erisilebilir: bool | None
    guven_skoru: GuvenSkoruYaniti | None
    referanslar: list[ReferansDurumuYaniti]
    # Kartın "Kanıt bekliyor" rozeti: kanıt ya da referans eklenince arayüz
    # sayfayı yenilemeden günceller.
    kart_kanit_bekleyen: bool
    # Gencin itirazı GİRVAK'ta bekliyor (hak doldu ya da karara itiraz; docs/dogrulama.md § 9);
    # arayüz itirazı kapatır.
    inceleme_bekliyor: bool = False
    # GİRVAK'ın geçerli "doğrulanamadı" kararı (kalemin etiketi; puan değişmez, İ1).
    # Genç görür ve itiraz edebilir; GİRVAK "sorun yok" derse kalkar.
    dogrulanamadi: bool = False
    # Kararlardaki GİRVAK notları (boş olanlar atlanır)
    girvak_notlari: list[str] = []


class ReferansIstegiYaniti(BaseModel):
    """Referans kişinin yanıt vermeden ÖNCE gördüğü bilgi.

    Neyi onayladığını bilmeden puan vermek anlamsız; iddianın başlığı ve
    açıklaması bu yüzden burada.

    `iddia_sahibi_adi` DÖNÜYOR, iletişim bilgisi DÖNMÜYOR: referans kişi kimin
    için konuştuğunu bilmeli, yoksa yanıtı bir şey ifade etmez — zaten iddia
    sahibi onu bizzat referans gösterdi, taraflar birbirini tanıyor. E-posta,
    telefon ve kartın geri kalanı burada yok; bu uç nokta girişsiz çalıştığı
    için yalnızca yanıt vermeye yetecek kadarını açıyor (agent-specs.md § 1.5
    aynı çizgide: kart görünür, iletişim iki taraf da onaylayınca açılır).
    """

    somut_cikti_id: uuid.UUID
    baslik: str
    aciklama: str | None
    iddia_sahibi_adi: str
    # Formun (3) ve (4). sorusu bunları ayrı satırda gösterir; boşsa soru sorulmaz.
    pay: str | None = None
    sonuc: str | None = None
    # "bekliyor" | "yanitlandi" | "yanit_yok" | "geri_cekildi"
    durum: str
    # Arayüz formu gösterip göstermeyeceğine buna bakarak karar verir.
    yanitlanabilir: bool


class ReferansYanitiIstegi(BaseModel):
    """Girişsiz uç nokta: kimlik yerine tek kullanımlık token.

    Referans kişiyi üye olmaya zorlamak yanıt oranını düşürür
    (docs/api-contracts.md § Mimari Notlar).
    """

    token: str
    # 4 soruluk form (docs/dogrulama.md § 7): (1) ilişki, (2) çalışma, (3) pay, (4) sonuç.
    # Kalemde pay ya da sonuç yazılmamışsa o soru sorulmaz (null).
    iliski: Iliski
    iddia_dogru: FormCevabi
    pay_dogru: FormCevabi | None = None
    sonuc_dogru: FormCevabi | None = None
    yorum: str | None = Field(default=None, max_length=1000)


class ReferansYanitiSonucu(BaseModel):
    """Referans kişi yanıtını gönderdikten sonra gördüğü tek şey.

    Bu uç nokta girişsiz; eskiden kanıtın tam durumunu dönüyordu ve o yanıtta
    aynı çıktının BAŞKA referanslarının e-postası, puanı, yorumu ve yanıt
    token'ı vardı — referans kişi diğerlerinin yerine de yanıt verebiliyordu.
    Burada yalnızca neyi yanıtladığı ve yanıtının alındığı var.
    """

    baslik: str
    # "yanitlandi" — yanıtın alındığını söyler, olumlu olduğunu değil
    durum: str


class ItirazIstegi(BaseModel):
    """Değerlendirmeye itiraz. Yeni kanıt burada değil, kanıt bölümünden parça olarak
    eklenir (tek kapı)."""

    model_config = ConfigDict(extra="forbid")

    # Zorunlu: neyin gözden kaçtığı yazılmadan itiraz zar atmaya döner.
    aciklama: str = Field(min_length=3, max_length=1000)
