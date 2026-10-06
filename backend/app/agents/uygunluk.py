"""Uygunluk kararı: benzerlik aday bulur, yapay zekâ doğrular, puanı kod verir.

Firma–firma eşleşmesinde (docs/matching-algorithm.md § 8) gerekçeyi yazan çağrı
aynı çağrıda bir de uygunluk kararı döner. Skor ve sıralama yine koddadır; karar
yalnızca "bu aday listeye girsin mi, girerse kısmen mi" sorusunu yanıtlar.

Bu modül saf kuraldır (model ve veritabanı çağrısı yok, yalnızca okuma filtresi
için SQL koşulu): hangi etiket geçerli, hangi kayıt görünür, yargılanan adaylardan
hangileri listelenir. İstem ve model çağrısı `app/agents/eslestirme.py`'de.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import ColumnElement, or_

from app.models.eslesme import Eslesme

UYGUN = "uygun"
KISMEN = "kismen"
UYGUN_DEGIL = "uygun_degil"
GECERLI_KARARLAR = (UYGUN, KISMEN, UYGUN_DEGIL)

# Benzerlik tabanını geçen adaylardan skoru en yüksek bu kadarı yargılanabilir;
# uygun_degil olmayanlardan ilk TOP_N'i listelenir. Ölçümde (sonuclar/2026-10-06-1527)
# 5 listelik yer için 8 aday yetiyor: elenenler ilk 8'in içinde kalıyor.
YARGI_N = 8


class UygunlukKarari(BaseModel):
    """Modelin yapılandırılmış çıktısı.

    Alan sırası önemli: model önce gerekçeyi yazar, karar yazdığı metne dayanır
    (ölçümde kullanılan sıra; tersi karara sonradan gerekçe uydurtuyor).
    """

    gerekce: str = Field(
        description="2-3 cümlelik gerekçe; adayın ihtiyaca karşılık veren ve eksik kalan yanları"
    )
    uygunluk: Literal["uygun", "kismen", "uygun_degil"] = Field(
        description="Gerekçeyle tutarlı uygunluk kararı"
    )


def karari_dogrula(etiket: str | None) -> str | None:
    """Geçerli etiket olduğu gibi, geçersiz ya da boş etiket "bilinmiyor" (None).

    Hata durumunda `uygun_degil` asla üretilmez: bilinmeyen aday bugünkü gibi
    listelenir ve sonraki hesapta yeniden denenir.
    """
    return etiket if etiket in GECERLI_KARARLAR else None


def gorunur_mu(uygunluk: str | None) -> bool:
    """`uygun_degil` dışındaki her şey (bilinmiyor dahil) görünür."""
    return uygunluk != UYGUN_DEGIL


def gosterilecek_karar(uygunluk: str | None, firma_adayi: bool) -> str | None:
    """Yanıtta rozet için dönen karar. Genç adayında hiçbir zaman: gençler için karar yalnızca
    listeden gizlemeye yarar (ölçümde iyi adaylara sık "kısmen" dedi; rozet gürültü olurdu)."""
    return uygunluk if firma_adayi else None


def gorunur_kosulu() -> ColumnElement[bool]:
    """Eşleşme okuyan her sorgunun kullandığı tek filtre: `uygun_degil` hiçbir yerde görünmez.

    Yeni bir okuma ucu yazarken `.where(gorunur_kosulu())` eklenir; kayıtlar
    veritabanında durur (tekrar tekrar model çağrısı olmasın), ekrana çıkmaz.
    """
    return or_(Eslesme.uygunluk.is_(None), Eslesme.uygunluk != UYGUN_DEGIL)


def listelenecekler(
    pencere: Sequence[uuid.UUID], kararlar: Mapping[uuid.UUID, str | None], n: int
) -> list[uuid.UUID]:
    """Skora göre sıralı yargı penceresinden, `uygun_degil` olmayan ilk `n` aday.

    Kararı bilinmeyen (None ya da `kararlar`da olmayan) aday listelenir.
    """
    return [kimlik for kimlik in pencere if gorunur_mu(kararlar.get(kimlik))][:n]
