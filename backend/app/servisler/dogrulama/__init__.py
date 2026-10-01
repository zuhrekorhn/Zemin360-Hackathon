"""Doğrulamanın orkestrasyonu (CLAUDE.md: uçlar ince, orkestrasyon burada).

Kurallar `app/agents/dogrulama/`'da (saf); burada modele uygulanmaları:
  - `parcalar`: kanıt parçası ekleme ve kaldırmanın tek kapısı
  - `kanit`: değerlendirme (rubrik), kanıt ekle / kaldır, `kanit_bekleyen` bayrağı
  - `referans`: referans isteme, yanıt, zaman aşımı, yeniden isteme
  - `itiraz`: itirazla yeniden değerlendirme

Sözleşme (kart düzenleme servisiyle aynı): servis modeli değiştirir; commit,
arka plan işi ve HTTP'ye çeviri (404, 409, 429) çağıran ucun işidir. Bildirim,
olayı yazan servisle aynı işlemde yazılır.
"""

from app.servisler.dogrulama.itiraz import itiraz_et
from app.servisler.dogrulama.kanit import (
    DegerlendirilecekKanitYok,
    ciktiyi_puanla,
    degerlendir,
    kanit_bekleyeni_guncelle,
    kanit_linki_ekle,
    kanit_parcasini_sil,
    rubrigi_yaz,
)
from app.servisler.dogrulama.parcalar import (
    KanitBulunamadi,
    KanitZatenVar,
    birincil_link,
    degerlendirildi_mi,
    link_parcasi_ekle,
)
from app.servisler.dogrulama.referans import (
    ReferansYenidenIstenemez,
    referans_guncel_mi,
    referans_iste,
    referans_yanitla,
    referansi_yeniden_iste,
    ucuncu_taraf_puani,
    yeniden_isteme_engeli,
    zaman_asimini_isle,
    zaman_asimlarini_isle,
)
from app.servisler.dogrulama.sorgular import CiktiBulunamadi, cikti_getir

__all__ = [
    "CiktiBulunamadi",
    "DegerlendirilecekKanitYok",
    "KanitBulunamadi",
    "KanitZatenVar",
    "ReferansYenidenIstenemez",
    "birincil_link",
    "cikti_getir",
    "ciktiyi_puanla",
    "degerlendir",
    "degerlendirildi_mi",
    "itiraz_et",
    "kanit_bekleyeni_guncelle",
    "kanit_linki_ekle",
    "kanit_parcasini_sil",
    "link_parcasi_ekle",
    "referans_guncel_mi",
    "referans_iste",
    "referans_yanitla",
    "referansi_yeniden_iste",
    "rubrigi_yaz",
    "ucuncu_taraf_puani",
    "yeniden_isteme_engeli",
    "zaman_asimini_isle",
    "zaman_asimlarini_isle",
]
