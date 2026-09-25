"""Müsaitlik: işin ne kadar süreyle / hangi biçimde yapıldığı.

Eşleştirme'nin sert filtrelerinden biri (`docs/matching-algorithm.md` § 3) ve
düz eşitlikle karşılaştırılıyor. Serbest metin olduğu sürece şehirde yaşanan
sessiz elemenin aynısı oluyordu: Tanımlama Ajanı "tam zamanlı" yazınca genç
tarafındaki `tam_zamanli` koduyla eşleşmiyor, TÜM adaylar skor hesaplanmadan
eleniyordu. Bu yüzden her iki taraf da yalnızca buradaki kodları saklıyor.

Çalışma modeliyle (iş yerinde / hibrit / uzaktan) karıştırma: o işin nerede
yapıldığı, bu ne kadar süreyle.

İki okuma biçimi var ve bilerek ayrı:
  - `musaitlik_kanonik` HOŞGÖRÜLÜ: tanınmayanı None yapar. Checkpoint'te
    duran eski taslaklar ve eski kayıtlar böyle okunur; eskiden serbest
    metin olan bir değer sohbet ucunu kırmamalı.
  - `musaitlik_dogrula` KATI: tanınmayanı reddeder. İstemciden gelen onay
    isteği böyle okunur; formda seçim listesi var, bilinmeyen bir değer
    gelmişse bu bir hatadır ve söylenmelidir.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BeforeValidator

from app.core.metin import sade_anahtar

TAM_ZAMANLI = "tam_zamanli"
YARIM_ZAMANLI = "yarim_zamanli"
PROJE_BAZLI = "proje_bazli"
STAJ = "staj"

MUSAITLIKLER: tuple[str, ...] = (TAM_ZAMANLI, YARIM_ZAMANLI, PROJE_BAZLI, STAJ)

# Şemalarda tip olarak kullanılır (LLM çıkarımı ve istek gövdeleri).
Musaitlik = Literal["tam_zamanli", "yarim_zamanli", "proje_bazli", "staj"]

ETIKETLER: dict[str, str] = {
    TAM_ZAMANLI: "Tam zamanlı",
    YARIM_ZAMANLI: "Yarı zamanlı",
    PROJE_BAZLI: "Proje bazlı",
    STAJ: "Staj",
}

# Kod ve etiket dışında sık görülen yazımlar. Kodlar ve etiketler zaten
# tanınıyor; burada yalnızca gerçekten farklı söylenişler var.
_ESANLAMLILAR: dict[str, str] = {
    "tam gün": TAM_ZAMANLI,
    "full time": TAM_ZAMANLI,
    "yarı gün": YARIM_ZAMANLI,
    "part time": YARIM_ZAMANLI,
    "proje": PROJE_BAZLI,
    "freelance": PROJE_BAZLI,
    "serbest": PROJE_BAZLI,
    "stajyer": STAJ,
    "internship": STAJ,
}

_ASCII = str.maketrans({"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c"})


def _anahtar(metin: str) -> str:
    """Boşluk, alt çizgi, büyük/küçük harf ve Türkçe karakter farkını siler.

    "Tam zamanlı", "tam-zamanli" ve "tam_zamanli" aynı anahtara düşer.
    """
    return sade_anahtar(metin).translate(_ASCII)


_ANAHTARLAR: dict[str, str] = {
    **{_anahtar(kod): kod for kod in MUSAITLIKLER},
    **{_anahtar(etiket): kod for kod, etiket in ETIKETLER.items()},
    **{_anahtar(soz): kod for soz, kod in _ESANLAMLILAR.items()},
}


def musaitlik_kanonik(deger: object) -> str | None:
    """Hoşgörülü okuma: bilinen yazımı koda çevirir, tanınmayanı None yapar."""
    if not isinstance(deger, str) or not deger.strip():
        return None
    return _ANAHTARLAR.get(_anahtar(deger))


def musaitlik_dogrula(deger: object) -> str | None:
    """Katı okuma: boş değer None, bilinen yazım kod, geri kalanı hata."""
    if deger is None or (isinstance(deger, str) and not deger.strip()):
        return None
    kod = musaitlik_kanonik(deger)
    if kod is None:
        gecerliler = ", ".join(MUSAITLIKLER)
        raise ValueError(f"Tanınmayan müsaitlik: {deger!r}. Geçerli değerler: {gecerliler}")
    return kod


# Şemalarda kullanılan iki tip — hangi okumanın nerede geçerli olduğu
# alan tanımında görünsün diye.
#   HOŞGÖRÜLÜ: checkpoint'ten okunan taslak; eski serbest metin None olur.
#   KATI:      istemcinin gönderdiği onay; tanınmayan değer 422 döner.
HosgoruluMusaitlik = Annotated[Musaitlik | None, BeforeValidator(musaitlik_kanonik)]
KatiMusaitlik = Annotated[Musaitlik | None, BeforeValidator(musaitlik_dogrula)]
