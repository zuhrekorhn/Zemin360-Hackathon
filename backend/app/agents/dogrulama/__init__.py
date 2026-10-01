"""Doğrulama Ajanı — somut çıktı iddialarına dört bileşenli güven göstergesi.

**Sohbet ajanı değil** (Eşleştirme gibi): çok turlu konuşma yok, üç ayrı
tek seferlik akış var — kanıt kontrolü, referans akışı, itiraz. Bu yüzden
`sohbet_motoru.py` kullanılmıyor.

docs/agent-specs.md § 4. Sınırlar oradan:
  - "Bu kişi yalan söylüyor" gibi kesin hüküm vermez, sinyal toplar.
  - Kanıtsız kartı sistemden dışlamaz, sadece "doğrulanmamış" etiketler.
  - Üçüncü taraf onayını zorunlu kılmaz — zaman aşımı bir ceza değil, nötr
    bir durumdur (docs/sequence-diagrams.md § Akış 2, else dalı).
  - Rubrik kriterleri objektif ve kontrol edilebilir olmalı; "ne kadar
    etkileyici yazılmış" gibi öznel kriterler önyargı üretir (madde 5).

Paket düzeni (docs/plans/dogrulama-iyilestirme.md § 14.1):
  - `referans_durumu`: referans isteğinin durumları, geçişleri, zaman aşımı
  - `kurallar`: saf kurallar (referans puanı, üçüncü taraf onayı, geçerlilik)
  - `link_kontrolu`: linkin erişilebilirliği ve özeti (adım 5'te okuyucu zinciri)
  - `rubrik`: modelin ön rubriği (adım 4'te çıkarım + kural çekirdeği)

Dışarıya açılan adlar burada toplanır; içe aktaranlar alt modülü bilmek zorunda değil.
"""

from app.agents.dogrulama.kurallar import (
    REFERANS_PUAN_ESLEMESI,
    ZATEN_BEKLENIYOR,
    ReferansYaniti,
    gecerli_referans_puanlari,
    otomatik_puanlanir_mi,
    referans_gecerli_mi,
    referans_puanina_cevir,
    referans_yeniden_istenebilir_mi,
    ucuncu_taraf_onayi_hesapla,
)
from app.agents.dogrulama.link_kontrolu import (
    LinkKontrolu,
    link_ozetini_cikar,
    linki_kontrol_et,
    linki_normalize_et,
)
from app.agents.dogrulama.referans_durumu import (
    DURUM_BEKLIYOR,
    DURUM_YANIT_YOK,
    DURUM_YANITLANDI,
    REFERANS_TIMEOUT_GUN,
    zaman_asimina_ugradi_mi,
)
from app.agents.dogrulama.rubrik import RUBRIK_SABLONU, RUBRIK_TALIMATI, RubrikPuani, rubrik_puanla

__all__ = [
    "DURUM_BEKLIYOR",
    "DURUM_YANITLANDI",
    "DURUM_YANIT_YOK",
    "REFERANS_PUAN_ESLEMESI",
    "REFERANS_TIMEOUT_GUN",
    "RUBRIK_SABLONU",
    "RUBRIK_TALIMATI",
    "ZATEN_BEKLENIYOR",
    "LinkKontrolu",
    "ReferansYaniti",
    "RubrikPuani",
    "gecerli_referans_puanlari",
    "link_ozetini_cikar",
    "linki_kontrol_et",
    "linki_normalize_et",
    "otomatik_puanlanir_mi",
    "referans_gecerli_mi",
    "referans_puanina_cevir",
    "referans_yeniden_istenebilir_mi",
    "rubrik_puanla",
    "ucuncu_taraf_onayi_hesapla",
    "zaman_asimina_ugradi_mi",
]
