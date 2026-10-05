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


class DosyaSiniri(ValueError):
    """Çalışmanın dosya sınırı doldu (uçta 422); mesaj gence gösterilir."""


# Çalışma başına en çok dosya / görsel (plan § 4.4)
KALEM_BASINA_DOSYA = 5
DOSYA_TURLERI = frozenset({ParcaTuru.DOSYA.value, ParcaTuru.GORSEL.value})


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


def dosya_eklenebilir_mi(cikti: SomutCikti, dosya_ozeti: str | None = None) -> None:
    """Sınır dolduysa `DosyaSiniri`, aynı dosya varsa `KanitZatenVar`; dosya
    işlenmeden ve depoya konmadan önce sorulur."""
    if dosya_ozeti and any(p.dosya_ozeti == dosya_ozeti for p in cikti.kanit_parcalari):
        raise KanitZatenVar("Bu dosya bu çalışmada zaten var.")
    sayi = sum(1 for p in cikti.kanit_parcalari if p.tur in DOSYA_TURLERI)
    if sayi >= KALEM_BASINA_DOSYA:
        raise DosyaSiniri(
            f"Bir çalışmaya en çok {KALEM_BASINA_DOSYA} dosya ekleyebilirsin; "
            "yenisini eklemek için birini kaldır."
        )


def dosya_parcasi_ekle(
    cikti: SomutCikti,
    *,
    tur: ParcaTuru,
    dosya_anahtari: str,
    dosya_ozeti: str,
    belge: dict,
    tam_metin: str | None = None,
    gorsel_metni: str | None = None,
    phash: str | None = None,
) -> KanitParcasi:
    """Çalışmaya dosya ya da görsel parçası ekler; aynı dosya (ham özet) ikinci kez 409."""
    dosya_eklenebilir_mi(cikti, dosya_ozeti)
    parca = KanitParcasi(
        tur=tur.value,
        dosya_anahtari=dosya_anahtari,
        dosya_ozeti=dosya_ozeti,
        phash=phash,
        belge=belge,
        tam_metin=tam_metin,
        gorsel_metni=gorsel_metni,
    )
    cikti.kanit_parcalari.append(parca)
    gostergeyi_yeniden_degerlendirmeye_al(cikti)
    return parca


def parca_bul(cikti: SomutCikti, parca_id: uuid.UUID) -> KanitParcasi:
    for parca in cikti.kanit_parcalari:
        if parca.id == parca_id:
            return parca
    raise KanitBulunamadi(parca_id)


def parca_sil(cikti: SomutCikti, parca_id: uuid.UUID) -> KanitParcasi:
    """Parçayı kaldırır; göstergenin değerlendirme kısmı sıfırlanır. Döner: kaldırılan
    parça (dosyasını depodan silmek çağıranın işi, commit'ten sonra)."""
    parca = parca_bul(cikti, parca_id)
    cikti.kanit_parcalari.remove(parca)
    gostergeyi_yeniden_degerlendirmeye_al(cikti)
    return parca


def okunabilir_mi(parca: KanitParcasi) -> bool:
    """Değerlendirmenin okuyacağı parça mı? Her parça okunur, başlık başına en
    güçlüsü kullanılır (plan § 2). Dosya ve görsel yüklenirken okunmuştur."""
    if parca.tur == ParcaTuru.LINK.value:
        return bool(parca.url)
    return parca.tur in DOSYA_TURLERI


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
    skor.girdi_ozeti = None
    skor.itiraz_sayisi = 0  # yeni girdi: itiraz hakkı tazelenir
