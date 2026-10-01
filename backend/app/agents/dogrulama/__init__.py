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
  - `okuma`: kanıt adresinin okunması (okuyucu zinciri: app/core/kanit_okuma/)
  - `cikarim`, `alinti`, `not_sablonu`, `cekirdek`: model gerçek çıkarır, kural
    puanlar, şablon anlatır (adım 4)

Dışarıya açılan adlar burada toplanır; içe aktaranlar alt modülü bilmek zorunda değil.
"""

from app.agents.dogrulama.kurallar import (
    ILISKILER,
    REFERANS_PUAN_ESLEMESI,
    YANITLAR,
    ZATEN_BEKLENIYOR,
    ReferansDestegi,
    ReferansYaniti,
    eposta_gucu,
    gecerli_referans_yanitlari,
    referans_basligi,
    referans_destegi,
    referans_gecerli_mi,
    referans_puanina_cevir,
    referans_yeniden_istenebilir_mi,
    ucuncu_taraf_onayi_hesapla,
)
from app.agents.dogrulama.referans_durumu import (
    DURUM_BEKLIYOR,
    DURUM_GERI_CEKILDI,
    DURUM_YANIT_YOK,
    DURUM_YANITLANDI,
    HATIRLATMA_GUN,
    OLAY_GERI_CEK,
    OLAY_YANIT,
    OLAY_ZAMAN_ASIMI,
    REFERANS_TIMEOUT_GUN,
    GecersizReferansGecisi,
    hatirlatma_zamani_mi,
    referans_gecisi,
    yanitlanabilir_mi,
    zaman_asimina_ugradi_mi,
)

__all__ = [
    "DURUM_BEKLIYOR",
    "DURUM_GERI_CEKILDI",
    "DURUM_YANITLANDI",
    "DURUM_YANIT_YOK",
    "HATIRLATMA_GUN",
    "ILISKILER",
    "OLAY_GERI_CEK",
    "OLAY_YANIT",
    "OLAY_ZAMAN_ASIMI",
    "REFERANS_PUAN_ESLEMESI",
    "REFERANS_TIMEOUT_GUN",
    "YANITLAR",
    "ZATEN_BEKLENIYOR",
    "GecersizReferansGecisi",
    "ReferansDestegi",
    "ReferansYaniti",
    "eposta_gucu",
    "gecerli_referans_yanitlari",
    "hatirlatma_zamani_mi",
    "referans_basligi",
    "referans_destegi",
    "referans_gecerli_mi",
    "referans_gecisi",
    "referans_puanina_cevir",
    "referans_yeniden_istenebilir_mi",
    "ucuncu_taraf_onayi_hesapla",
    "yanitlanabilir_mi",
    "zaman_asimina_ugradi_mi",
]
