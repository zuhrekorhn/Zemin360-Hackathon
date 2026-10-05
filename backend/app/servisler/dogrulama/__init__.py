"""Doğrulamanın orkestrasyonu (CLAUDE.md: uçlar ince, orkestrasyon burada).

Kurallar `app/agents/dogrulama/`'da (saf); burada modele uygulanmaları:
  - `parcalar`: kanıt parçası ekleme ve kaldırmanın tek kapısı
  - `kanit`: değerlendirme (rubrik), kanıt ekle / kaldır, `kanit_bekleyen` bayrağı
  - `referans`: referans isteme, yanıt, geri çekme, zaman aşımı, hatırlatma, yeniden isteme
  - `referans_epostasi`: referans kişiye giden e-postalar
  - `itiraz`: itirazla yeniden değerlendirme
  - `dosyalar`: dosya ve görsel kanıtı (yükleme hattı, depo, indirme adresi)

Sözleşme (kart düzenleme servisiyle aynı): servis modeli değiştirir; commit,
arka plan işi ve HTTP'ye çeviri (404, 409, 429, 202) çağıran ucun işidir. Bildirim,
olayı yazan servisle aynı işlemde yazılır.
"""

from app.servisler.dogrulama.curume import CurumeSonucu, curume_yoklamasi
from app.servisler.dogrulama.itiraz import ITIRAZ_SINIRI, ItirazIncelemede, itiraz_et
from app.servisler.dogrulama.kanit import (
    ciktiyi_puanla,
    degerlendir,
    kanit_bekleyeni_guncelle,
    kanit_linki_ekle,
    kanit_parcasini_sil,
)
from app.servisler.dogrulama.parcalar import (
    KanitBulunamadi,
    KanitZatenVar,
    degerlendirildi_mi,
    link_parcasi_ekle,
    okunabilir_mi,
    parca_bul,
)
from app.servisler.dogrulama.referans import (
    FormYaniti,
    KendiReferansi,
    ReferansYenidenIstenemez,
    ReferansZatenBekliyor,
    istek_epostasi_hazirla,
    istek_epostasi_kur,
    isteme_engeli,
    referans_destegi_hesapla,
    referans_guncel_mi,
    referans_iste,
    referans_taramasi,
    referans_yanitla,
    referansi_geri_cek,
    referansi_yeniden_iste,
    ucuncu_taraf_puani,
    yeni_istek_ac,
    yeniden_isteme_engeli,
    zaman_asimini_isle,
    zaman_asimlarini_isle,
)
from app.servisler.dogrulama.sorgular import CiktiBulunamadi, cikti_getir

__all__ = [
    "CurumeSonucu",
    "curume_yoklamasi",
    "ITIRAZ_SINIRI",
    "CiktiBulunamadi",
    "ItirazIncelemede",
    "KanitBulunamadi",
    "KanitZatenVar",
    "FormYaniti",
    "KendiReferansi",
    "ReferansYenidenIstenemez",
    "ReferansZatenBekliyor",
    "okunabilir_mi",
    "cikti_getir",
    "ciktiyi_puanla",
    "degerlendir",
    "degerlendirildi_mi",
    "itiraz_et",
    "kanit_bekleyeni_guncelle",
    "kanit_linki_ekle",
    "kanit_parcasini_sil",
    "link_parcasi_ekle",
    "parca_bul",
    "isteme_engeli",
    "istek_epostasi_hazirla",
    "istek_epostasi_kur",
    "referans_destegi_hesapla",
    "referans_guncel_mi",
    "referans_iste",
    "referans_taramasi",
    "referans_yanitla",
    "referansi_geri_cek",
    "referansi_yeniden_iste",
    "ucuncu_taraf_puani",
    "yeni_istek_ac",
    "yeniden_isteme_engeli",
    "zaman_asimini_isle",
    "zaman_asimlarini_isle",
]
