"""Tanımlama Ajanı uç noktalarının istek/yanıt şemaları.

docs/api-contracts.md § Tanımlama, docs/data-schema.md § IHTIYAC_KARTI.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from app.core.firma_karti import IsbirligiTuru
from app.core.firma_profili import FirmaTuru
from app.core.ilan import Aranan, KapanmaNedeni
from app.core.musaitlik import HosgoruluMusaitlik, KatiMusaitlik

# Taslak ekranındaki metin alanlarının üst sınırı (formdaki maxLength ile aynı)
PROBLEM_EN_UZUN = 1000
KRITER_EN_UZUN = 500


def _kirp(deger: Any) -> Any:
    """Baştaki/sondaki boşluk atılır; boş kalan metin None."""
    if isinstance(deger, str):
        return deger.strip() or None
    return deger


KirpilmisMetin = Annotated[str | None, BeforeValidator(_kirp)]

# Başarı ölçütünün her parçası kısa bir ifade ("ayda %10", "3 ay içinde")
OLCUT_EN_UZUN = 200


class BasariOlcutu(BaseModel):
    """Başarı kriterinin parçaları (app/core/basari_olcutu.py)."""

    metrik: str | None = None
    mevcut_deger: str | None = None
    hedef_deger: str | None = None
    sure: str | None = None
    olcum_bilinmiyor: bool = False


class BasariOlcutuGirdisi(BasariOlcutu):
    """Taslak ekranında düzeltilen ölçüt: kırpılır, uzunluk sınırlı."""

    metrik: KirpilmisMetin = Field(default=None, max_length=OLCUT_EN_UZUN)
    mevcut_deger: KirpilmisMetin = Field(default=None, max_length=OLCUT_EN_UZUN)
    hedef_deger: KirpilmisMetin = Field(default=None, max_length=OLCUT_EN_UZUN)
    sure: KirpilmisMetin = Field(default=None, max_length=OLCUT_EN_UZUN)


class IhtiyacTaslagi(BaseModel):
    """Kuruma onay için gösterilen taslak — henüz veritabanında değil.

    Checkpoint'ten okunurken kullanılıyor (sohbet uçlarının yanıtı ve düzeltme
    gönderilmeyen onay). Müsaitlik bu yüzden hoşgörülü: eskiden serbest metin
    olarak kaydedilmiş bir taslak sohbeti kırmamalı.
    """

    problem_tanimi: str | None = None
    basari_kriteri: str | None = None
    # Sohbette çıkarılan parçalar; bu alandan önce açılmış sohbette yok.
    basari_olcutu: BasariOlcutu | None = None
    kisitlar: str | None = None
    # Eşleştirme'nin sert filtreleri bu alanlardan çalışıyor (data-schema.md)
    sehir_tercihi: str | None = None
    # Tek seçim: is_yerinde | hibrit | uzaktan. "Uzaktan" seçilirse şehir
    # filtresi uygulanmaz.
    calisma_modeli: str | None = None
    musaitlik_tercihi: HosgoruluMusaitlik = None
    # Ortak ilanı (docs/plans/firma-akisi.md § 5); genç ilanında boş.
    aranan_firma_turleri: list[str] = []
    isbirligi_turu: str | None = None


class IhtiyacTaslagiGirdisi(IhtiyacTaslagi):
    """Kurumun onay formunda düzelttiği taslak — istemciden gelir, katı okunur.

    Formda seçim listesi var; listede olmayan bir müsaitlik gelmişse sessizce
    atmak yerine 422 ile söylüyoruz.
    """

    # Metin alanları taslak ekranında düzenlenebiliyor: yalnızca boşluktan
    # oluşan metin boş sayılır (onay zorunlu alanı reddeder), uzunluk sınırlı.
    problem_tanimi: KirpilmisMetin = Field(default=None, max_length=PROBLEM_EN_UZUN)
    basari_kriteri: KirpilmisMetin = Field(default=None, max_length=KRITER_EN_UZUN)
    basari_olcutu: BasariOlcutuGirdisi | None = None
    kisitlar: KirpilmisMetin = Field(default=None, max_length=KRITER_EN_UZUN)
    musaitlik_tercihi: KatiMusaitlik = None
    aranan_firma_turleri: list[FirmaTuru] = []
    isbirligi_turu: IsbirligiTuru | None = None


class TanimlamaBaslatIstegi(BaseModel):
    """Hangi kapı: genç yetenek (varsayılan) ya da iş birliği ortağı."""

    model_config = ConfigDict(extra="forbid")

    aranan: Aranan = "genc"


class TanimlamaSohbetYaniti(BaseModel):
    oturum_id: uuid.UUID
    aranan: str = "genc"
    soru: str | None = None
    taslak: IhtiyacTaslagi
    taslak_hazir: bool


class KurumProfili(BaseModel):
    """İhtiyaç kartı onayıyla gelen kurum profili güncellemesi (Faz B not § 4).

    Kimlik token'daki hesaptan; kurumun adı ve iletişim e-postası kayıtta
    alındı. Boş gelen alan kayıtlı değeri silmez.
    """

    sektor: str | None = None
    sehir: str | None = None


class IhtiyacKartiOnaylaIstegi(BaseModel):
    oturum_id: uuid.UUID
    kurum_profili: KurumProfili = Field(default_factory=KurumProfili)
    duzeltilmis_taslak: IhtiyacTaslagiGirdisi | None = None


class KurumYaniti(BaseModel):
    """Kartla birlikte gösterilen kurum bilgisi — iletişim e-postası YOK.

    `id` gerekli: Eşleştirme önerileri kurum kimliğiyle okunuyor
    (`GET /eslestirme/oneriler/{kurum_id}`), kartı onaylayan arayüzün bu
    kimliği öğrenebileceği başka bir yer yoktu. Kimlik iletişim bilgisi
    değil — gizlilik kuralı (agent-specs.md § 1.5) etkilenmiyor.
    """

    id: uuid.UUID
    ad: str
    # "Doğrulanmış firma" işareti (docs/plans/firma-akisi.md § 0 karar 17).
    # Durumun kendisi (bekliyor / şimdilik değil) yalnızca GİRVAK'a.
    dogrulandi: bool = False
    sektor: str | None
    sehir: str | None


class IhtiyacKartiYaniti(BaseModel):
    """Kartın dışarıya açılan hali.

    Eşleştirme Ajanı da bu görünümü okuyacak (api-contracts.md). Kurumun
    iletişim e-postası burada yok: Keşif tarafındaki gizlilik kuralının
    karşılığı (agent-specs.md § 1.5) — iletişim iki taraf da onaylayınca açılır.
    """

    id: uuid.UUID
    problem_tanimi: str
    basari_kriteri: str | None
    basari_olcutu: BasariOlcutu | None = None
    # Hedef değeri olmayan ölçüt: kartta "ölçüm yöntemi belirlenecek"
    olcum_belirlenecek: bool = False
    kisitlar: str | None
    sehir_tercihi: str | None
    calisma_modeli: str | None
    musaitlik_tercihi: str | None
    embedding_var: bool
    kurum: KurumYaniti
    # acik | kapandi. Kapanma nedeni burada yok: yalnızca GİRVAK görür.
    durum: str = "acik"
    # genc | firma (docs/plans/firma-akisi.md § 0 kararlar 4-5)
    aranan: str = "genc"
    aranan_firma_turleri: list[str] = []
    isbirligi_turu: str | None = None


class IhtiyacKartiKapatIstegi(BaseModel):
    """Kapatma nedeni zorunlu (docs/plans/firma-akisi.md § 0 karar 7)."""

    model_config = ConfigDict(extra="forbid")

    neden: KapanmaNedeni
