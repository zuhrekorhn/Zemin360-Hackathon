"""Şehir adlarının tek biçimli tutulması ve Türkçe'ye duyarlı karşılaştırma.

Neden gerekli: Eşleştirme'nin tek sert metin filtresi şehir
(`docs/matching-algorithm.md` § 3). Serbest yazımda "istanbul" ile "İstanbul"
farklı iki değer oluyor ve aday skor hesaplanmadan, sessizce eleniyor.

Türkçe'de bunun akla gelen çözümleri çalışmıyor — hepsi bu veritabanında
denendi:

    'İstanbul' = 'istanbul'          -> false
    lower('İstanbul')                -> 'İstanbul'   (Postgres İ'yi küçültmüyor)
    'İstanbul' ILIKE 'istanbul'      -> false
    Python "İstanbul".lower()        -> 'i̇stanbul'  (i + U+0307, yine eşit değil)

Bu yüzden katlama elle yapılıyor: I→ı, İ→i eşlemesi, ardından küçültme ve
artık kalan birleşen noktanın (U+0307) temizliği.

Kayıt anında değer kanonik yazıma çevriliyor; karşılaştırma da aynı fonksiyondan
geçiyor. İkisi birlikte olmazsa eski kayıtlar yeni yazımla eşleşmez.
"""

from __future__ import annotations

import unicodedata

# Kullanıcı "fark etmez / uzaktan" dediğinde saklanan değer.
# Genç için "her şehirden çalışırım", kurum için "şehir filtresi uygulama".
UZAKTAN = "uzaktan"

# 81 il, kanonik yazımıyla.
SEHIRLER: tuple[str, ...] = (
    "Adana",
    "Adıyaman",
    "Afyonkarahisar",
    "Ağrı",
    "Aksaray",
    "Amasya",
    "Ankara",
    "Antalya",
    "Ardahan",
    "Artvin",
    "Aydın",
    "Balıkesir",
    "Bartın",
    "Batman",
    "Bayburt",
    "Bilecik",
    "Bingöl",
    "Bitlis",
    "Bolu",
    "Burdur",
    "Bursa",
    "Çanakkale",
    "Çankırı",
    "Çorum",
    "Denizli",
    "Diyarbakır",
    "Düzce",
    "Edirne",
    "Elazığ",
    "Erzincan",
    "Erzurum",
    "Eskişehir",
    "Gaziantep",
    "Giresun",
    "Gümüşhane",
    "Hakkâri",
    "Hatay",
    "Iğdır",
    "Isparta",
    "İstanbul",
    "İzmir",
    "Kahramanmaraş",
    "Karabük",
    "Karaman",
    "Kars",
    "Kastamonu",
    "Kayseri",
    "Kırıkkale",
    "Kırklareli",
    "Kırşehir",
    "Kilis",
    "Kocaeli",
    "Konya",
    "Kütahya",
    "Malatya",
    "Manisa",
    "Mardin",
    "Mersin",
    "Muğla",
    "Muş",
    "Nevşehir",
    "Niğde",
    "Ordu",
    "Osmaniye",
    "Rize",
    "Sakarya",
    "Samsun",
    "Siirt",
    "Sinop",
    "Sivas",
    "Şanlıurfa",
    "Şırnak",
    "Tekirdağ",
    "Tokat",
    "Trabzon",
    "Tunceli",
    "Uşak",
    "Van",
    "Yalova",
    "Yozgat",
    "Zonguldak",
)

# Türkçe'de büyük/küçük eşleniği ASCII'den farklı olan iki harf.
_BUYUK_ESLEME = str.maketrans({"I": "ı", "İ": "i"})
_BIRLESEN_NOKTA = "̇"


def turkce_kucult(metin: str) -> str:
    """Türkçe'ye duyarlı küçültme: I→ı, İ→i, sonra normal küçültme."""
    hazir = unicodedata.normalize("NFC", metin).translate(_BUYUK_ESLEME)
    return hazir.lower().replace(_BIRLESEN_NOKTA, "")


def sehir_anahtari(sehir: str) -> str:
    """Karşılaştırma anahtarı: boşluklar sadeleşir, harfler katlanır."""
    return " ".join(turkce_kucult(sehir).split())


# Türkçe klavyesi olmayan biri "IZMIR" ya da "Mugla" yazıyor. Bunlar Türkçe
# kurallarına göre başka kelimeler ("ızmır"), ama kastedilen belli. Bu yüzden
# YAZMA anında ikinci bir deneme daha yapılıyor: aksanları ASCII'ye indir.
# Karşılaştırma katmanı bu esnekliği kullanmıyor — orası kanonik değerlerle
# çalıştığı için katı kalabiliyor.
_ASCII_ESLEME = str.maketrans(
    {
        "ı": "i",
        "İ": "i",
        "I": "i",
        "i": "i",
        "ş": "s",
        "Ş": "s",
        "ğ": "g",
        "Ğ": "g",
        "ü": "u",
        "Ü": "u",
        "ö": "o",
        "Ö": "o",
        "ç": "c",
        "Ç": "c",
        "â": "a",
        "Â": "a",
    }
)


def _ascii_anahtari(sehir: str) -> str:
    return " ".join(sehir.translate(_ASCII_ESLEME).lower().split())


_ANAHTARLAR = {sehir_anahtari(sehir): sehir for sehir in SEHIRLER}
_ASCII_ANAHTARLAR = {_ascii_anahtari(sehir): sehir for sehir in SEHIRLER}

# Sohbetten gelen serbest metin de aynı kovaya düşsün: Tanımlama Ajanı
# şehir tercihini konuşmadan çıkarıyor, kullanıcı "uzaktan" demiş olabilir.
_UZAKTAN_ESANLAMLILARI = frozenset(
    {
        "uzaktan",
        "uzak",
        "remote",
        "fark etmez",
        "farketmez",
        "farketmiyor",
        "fark etmiyor",
        "her yerden",
        "online",
        "hibrit degil",
    }
)


def sehir_kanonik(sehir: str | None) -> str | None:
    """Girilen şehri kanonik yazıma çevirir.

    Listede yoksa (ilçe adı, yurt dışı, ajanın sohbetten çıkardığı serbest
    metin) değer atılmıyor — yalnızca kırpılıyor. Bilmediğimiz bir yeri
    sessizce silmek, yanlış yazmaktan daha kötü olurdu.
    """
    if sehir is None:
        return None
    kirpik = sehir.strip()
    if not kirpik:
        return None
    anahtar = sehir_anahtari(kirpik)
    if anahtar in _UZAKTAN_ESANLAMLILARI:
        return UZAKTAN
    if anahtar in _ANAHTARLAR:
        return _ANAHTARLAR[anahtar]
    return _ASCII_ANAHTARLAR.get(_ascii_anahtari(kirpik), kirpik)


def sehirler_esit_mi(birinci: str | None, ikinci: str | None) -> bool:
    """İki şehir adı aynı yeri mi gösteriyor? (yazım farkına bakmadan)"""
    if birinci is None or ikinci is None:
        return False
    return sehir_anahtari(birinci) == sehir_anahtari(ikinci)


def sehir_filtresi_gerekli_mi(sehir_tercihi: str | None) -> bool:
    """Kurum "uzaktan / fark etmez" dediyse şehir filtresi uygulanmaz."""
    kanonik = sehir_kanonik(sehir_tercihi)
    return kanonik is not None and kanonik != UZAKTAN
