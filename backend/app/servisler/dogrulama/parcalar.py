"""Kanıt parçalarının modele yazılması: tek kapı (plan § 1 İ7, bulgu 25).

Kanıt yalnızca buradan eklenir ve kaldırılır: kart sayfasının kanıt bölümü,
"çalışma ekle" formu ve Keşif onayı aynı fonksiyonları çağırır. Saf model
işlemi: veritabanı sorgusu, LLM ve commit yok; bu yüzden hem Doğrulama hem
kart düzenleme servisi döngüsüz kullanabilir.

Kanıt değişince ne olur (plan § 2: kanıt eklemek puanı hiçbir zaman düşürmez):
  - Göstergenin değerlendirme kısmı (Kanıt, Sonuç, Rol, not) sıfırlanır ve
    yeniden değerlendirilir; Referans başlığı korunur.
  - `icerik_tarihi` İLERLEMEZ: kanıt iddiayı değiştirmez, referans yanıtları
    geçerli kalır. Referansları geçmişe atan yalnızca iddianın kendisinin
    (başlık, açıklama, sonuç, pay) değişmesidir (genc-akisi § 0, karar 8).
"""

from __future__ import annotations

import uuid

from app.core.kanit_okuma.adres import normal_url
from app.core.kanit_okuma.belge import ParcaTuru
from app.models.kanit_parcasi import KanitParcasi
from app.models.somut_cikti import SomutCikti


class KanitZatenVar(ValueError):
    """Aynı link bu çalışmada zaten var (uçta 409)."""


class KanitBulunamadi(LookupError):
    """Parça bu çalışmaya ait değil ya da yok (uçta 404)."""


def link_parcasi_ekle(cikti: SomutCikti, url: str) -> KanitParcasi:
    """Çalışmaya link parçası ekler; göstergenin değerlendirme kısmı sıfırlanır.

    `cikti.kanit_parcalari` yüklenmiş olmalı (yeni kalemde boş liste).
    """
    temiz = url.strip()
    if not temiz:
        raise ValueError("Kanıt linki boş olamaz.")
    kimlik = normal_url(temiz)
    if any(p.normal_url == kimlik for p in cikti.kanit_parcalari):
        raise KanitZatenVar("Bu link bu çalışmada zaten var.")
    parca = KanitParcasi(tur=ParcaTuru.LINK.value, url=temiz, normal_url=kimlik)
    cikti.kanit_parcalari.append(parca)
    gostergeyi_yeniden_degerlendirmeye_al(cikti)
    return parca


def parca_sil(cikti: SomutCikti, parca_id: uuid.UUID) -> None:
    """Parçayı kaldırır; göstergenin değerlendirme kısmı sıfırlanır."""
    for parca in cikti.kanit_parcalari:
        if parca.id == parca_id:
            cikti.kanit_parcalari.remove(parca)
            gostergeyi_yeniden_degerlendirmeye_al(cikti)
            return
    raise KanitBulunamadi(parca_id)


def birincil_link(cikti: SomutCikti) -> str | None:
    """Değerlendirmenin okuduğu link: ilk eklenen link parçası.

    Adım 4-5'e kadar değerlendirme tek link okur; sonra her parça okunur ve
    başlık başına en güçlüsü seçilir (plan § 2).
    """
    for parca in cikti.kanit_parcalari:
        if parca.tur == ParcaTuru.LINK.value and parca.url:
            return parca.url
    return None


def degerlendirildi_mi(cikti: SomutCikti) -> bool:
    """Göstergenin değerlendirme kısmı hesaplandı mı? (Referans tek başına sayılmaz.)"""
    return cikti.guven_skoru is not None and cikti.guven_skoru.degerlendirme_tarihi is not None


def gostergeyi_yeniden_degerlendirmeye_al(cikti: SomutCikti) -> None:
    """Kanıt değişti: Kanıt, Sonuç, Rol ve not boşalır, Referans kalır.

    Değerlendirme (uçta eşzamanlı ya da kart hazırlamada arka planda) bunları
    yeniden yazar. Gösterge yoksa yapılacak bir şey yok.
    """
    skor = cikti.guven_skoru
    if skor is None:
        return
    skor.kanit_orijinalligi = None
    skor.sonuc_olculebilirligi = None
    skor.rol_netligi = None
    skor.gerekce_metni = None
    skor.degerlendirme_tarihi = None
