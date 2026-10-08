"""Keşif Ajanı uç noktalarının istek/yanıt şemaları (docs/api-contracts.md § Keşif)."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

from app.core.is_kalemi import IsTuru, is_turu_hosgorulu
from app.core.musaitlik import KatiMusaitlikler
from app.schemas.dogrulama import GuvenSkoruYaniti, KanitParcasiYaniti
from app.schemas.kart_duzenleme import (
    MAX_CALISMA,
    DeneyimSeviyesi,
    DoluKisaMetin,
    Etiketler,
    Metin,
)
from app.schemas.sohbet import SohbetBaslatIstegi, SohbetCevapIstegi

__all__ = ["SohbetBaslatIstegi", "SohbetCevapIstegi"]


class SomutCiktiTaslagi(BaseModel):
    """İş kalemi taslağı. Sonuç ve rol ayrı alanlar (düzenlenebilsinler diye);
    referans e-postası onayda iş kalemine referans isteği olarak bağlanır."""

    baslik: str
    aciklama: str | None = None
    kanit_linki: str | None = None
    # Hoşgörülü: checkpoint'teki eski taslaklarda yok; tanınmayan tür None olur.
    is_turu: Annotated[IsTuru | None, BeforeValidator(is_turu_hosgorulu)] = None
    olculebilir_sonuc: str | None = None
    kendi_rolu: str | None = None
    referans_email: str | None = None


class KartTaslagi(BaseModel):
    """Kullanıcıya onay için gösterilen taslak — henüz veritabanında değil."""

    rol_alani: str | None = None
    deneyim_seviyesi: str | None = None
    sektor_ilgi_alani: list[str] = Field(default_factory=list)
    araclar_teknolojiler: list[str] = Field(default_factory=list)
    sertifikalar: list[str] = Field(default_factory=list)
    diller: list[str] = Field(default_factory=list)
    somut_ciktilar: list[SomutCiktiTaslagi] = Field(default_factory=list)


def _etiketleri_temizle(deger: object) -> object:
    """Boş ve tekrarlanan etiketleri atar: sohbetin çıktısı kusurlu olabilir, sınır
    kontrolü yalnızca gerçekten fazla olanı yakalasın."""
    if not isinstance(deger, list):
        return deger
    temiz: list[str] = []
    for oge in deger:
        metin = oge.strip() if isinstance(oge, str) else oge
        if metin and metin not in temiz:
            temiz.append(metin)
    return temiz


OnayEtiketleri = Annotated[Etiketler, BeforeValidator(_etiketleri_temizle)]


class OnayliCikti(BaseModel):
    """Onaydaki bir çalışmanın sınırları: kart düzenlemedeki `IsKalemiGirdisi` ile aynı."""

    baslik: DoluKisaMetin
    aciklama: Metin | None = None
    olculebilir_sonuc: Metin | None = None
    kendi_rolu: Metin | None = None
    kanit_linki: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = (
        None
    )
    referans_email: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=254)] | None
    ) = None


class OnayliKart(BaseModel):
    """Onayda kaydedilecek kartın zorunlu alanları.

    Taslak (KartTaslagi) boş alan taşıyabilir, bu taşıyamaz. Tipler kart
    düzenlemeyle aynı: sohbetin yer tutucusu ("belirtilmedi") ya da tanınmayan
    bir deneyim seviyesi veritabanına giremez. Sektör eşleştirme metnine
    girdiği için en az bir tane; araçlar boş olabilir (çalışması olmayan genç).
    """

    rol_alani: DoluKisaMetin
    deneyim_seviyesi: DeneyimSeviyesi
    sektor_ilgi_alani: Annotated[OnayEtiketleri, Field(min_length=1)]
    # Kullanıcı taslakta her alanı düzenleyebiliyor: sınırlar sunucuda da olmalı, yoksa
    # tek bir onay isteği yüzlerce çalışma (yüzlerce değerlendirme ve e-posta) açabilir.
    araclar_teknolojiler: OnayEtiketleri = Field(default_factory=list)
    sertifikalar: OnayEtiketleri = Field(default_factory=list)
    diller: OnayEtiketleri = Field(default_factory=list)
    somut_ciktilar: list[OnayliCikti] = Field(default_factory=list, max_length=MAX_CALISMA)


class SohbetMesaji(BaseModel):
    """Sohbet geçmişinde bir balon: `ajan` (Zemin360) ya da `kullanici`."""

    kim: Literal["ajan", "kullanici"]
    metin: str


class SohbetDevamYaniti(BaseModel):
    """Yarım kalmış sohbeti geri yükler (sayfa yenilenince ya da sekme kapanınca)."""

    oturum_id: uuid.UUID
    mesajlar: list[SohbetMesaji]
    soru: str | None = None
    taslak: KartTaslagi
    taslak_hazir: bool


class SohbetYaniti(BaseModel):
    oturum_id: uuid.UUID
    # Taslak hazırsa soru yok; kullanıcıdan beklenen şey onay.
    soru: str | None = None
    taslak: KartTaslagi
    taslak_hazir: bool


class GencProfili(BaseModel):
    """Kart onayıyla gelen profil güncellemesi (docs/kimlik-ve-dongu.md § 4).

    Kimlik artık token'daki hesaptan geliyor; ad ve e-posta kayıtta alındı,
    burada yok. Boş gelen alan kayıtlı değeri SİLMEZ:
    profili kayıt formunda dolduran gencin onayı boş profil gönderir.
    """

    # Profilde şehir yoksa onay 422 döner: eşleştirmenin sert filtresi buna
    # bakıyor ve "belirtilmedi" bir yer değil (bkz. app/core/sehir.py).
    sehir: str | None = None
    # Kabul ettiği çalışma modelleri (is_yerinde | hibrit | uzaktan).
    # Müsaitlikten ayrı: o çalışma tipi, bu çalışma yeri.
    calisma_modelleri: list[str] = Field(default_factory=list)
    # Çoklu seçim, kod olarak saklanır (app/core/musaitlik.py): serbest metin
    # eşleştirme filtresinde sessiz elemeye yol açıyordu. Tanınmayan değer 422.
    musaitlikler: KatiMusaitlikler = Field(default_factory=list)


class KartOnaylaIstegi(BaseModel):
    oturum_id: uuid.UUID
    profil: GencProfili = Field(default_factory=GencProfili)
    # Kullanıcı taslakta düzeltme yaptıysa son hali; yoksa sohbetteki taslak kaydedilir.
    duzeltilmis_taslak: KartTaslagi | None = None


class SomutCiktiYaniti(BaseModel):
    """Kartla birlikte gösterilen çıktı.

    `guven_skoru` Doğrulama Ajanı'nın dört bileşenli rubriği; hiç kanıt
    eklenmemişse None kalır ("doğrulanmamış", ceza değil). Kart görünümüne
    buradan giriyor ki arayüz çıktı başına ayrıca /dogrulama/kanit/{id}
    çağırmak zorunda kalmasın — Eşleştirme önerileri de aynı görünümü
    kullandığı için skorun yanında rubrik bedavaya geliyor.
    """

    id: uuid.UUID
    baslik: str
    aciklama: str | None
    # Kanıt parçaları (link, ileride dosya / görsel); eklenme sırasıyla.
    kanitlar: list[KanitParcasiYaniti] = Field(validation_alias="kanit_parcalari")
    is_turu: str | None = None
    olculebilir_sonuc: str | None = None
    kendi_rolu: str | None = None
    guven_skoru: GuvenSkoruYaniti | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class YetenekKartiYaniti(BaseModel):
    """Kartın dışarıya açılan hali.

    E-posta BURADA YOK — agent-specs.md § 1.5: iletişim bilgisi kuruma
    varsayılan olarak gösterilmez, gencin kabulüyle açılır ve ayrı bir
    `iletisim` alanında taşınır (schemas/eslestirme.py). Gencin adı iletişim
    bilgisi sayılmıyor, baştan görünür (docs/kimlik-ve-dongu.md § 5).
    """

    id: uuid.UUID
    genc_adi: str
    rol_alani: str
    deneyim_seviyesi: str
    sektor_ilgi_alani: list[str]
    araclar_teknolojiler: list[str]
    sertifikalar: list[str] = Field(default_factory=list)
    diller: list[str] = Field(default_factory=list)
    kanit_bekleyen: bool
    versiyon: int
    embedding_var: bool
    somut_ciktilar: list[SomutCiktiYaniti]
    # İki tarafın her adımı onayladığı tamamlanmış iş birliği sayısı.
    # Kurum adı taşımaz; eşleşme skoruna doğrulama bonusu olarak girer.
    tamamlanan_pilot: int = 0

    model_config = {"from_attributes": True}
