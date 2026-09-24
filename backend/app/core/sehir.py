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

Burada YALNIZCA konum var. "Uzaktan" bir şehir değil, bir çalışma modeli —
`app/core/calisma_modeli.py` içinde duruyor.
"""

from __future__ import annotations

from app.core.metin import turkce_kucult

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
    if anahtar in _ANAHTARLAR:
        return _ANAHTARLAR[anahtar]
    return _ASCII_ANAHTARLAR.get(_ascii_anahtari(kirpik), kirpik)


def sehirler_esit_mi(birinci: str | None, ikinci: str | None) -> bool:
    """İki şehir adı aynı yeri mi gösteriyor? (yazım farkına bakmadan)"""
    if birinci is None or ikinci is None:
        return False
    return sehir_anahtari(birinci) == sehir_anahtari(ikinci)
