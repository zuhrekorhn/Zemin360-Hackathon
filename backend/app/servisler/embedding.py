"""Kartların embedding'i: tek hesap yeri (docs/matching-algorithm.md § 1-2).

Üç kart türü (yetenek, ihtiyaç, firma) aynı sözleşmeyle gömülür: temsil metni
kurulur, Voyage'a gider, sonuç karta yazılıp commit edilir. Voyage'a ulaşılamazsa
hata fırlatılmaz, False döner: kart zaten kayıtlı ve kaybolmamalı; embedding'i boş
kart eşleştirmeye girmez, sonraki hazırlama ya da "Eşleştirmeye hazırla" yeniden dener.

Temsil metni kart türüne göre `temsil_metni` üzerinden seçilir; yeni bir kart türü
kendi kaydını ekler, buradaki akış değişmez.
"""

from __future__ import annotations

import functools
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import (
    EmbeddingHatasi,
    embedding_uret,
    firma_temsil_metni,
    ihtiyac_temsil_metni,
    yetenek_temsil_metni,
)
from app.core.is_kalemi import is_kalemi_metni
from app.models.firma_karti import FirmaKarti
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.yetenek_karti import YetenekKarti

logger = logging.getLogger("zemin360.embedding")

Kart = YetenekKarti | IhtiyacKarti | FirmaKarti

EMBEDDING_HATA_MESAJI = (
    "Kart kaydedildi, ancak şu an eşleşmeye hazırlanamadı. Biraz sonra "
    "“Eşleştirmeye hazırla” ile yeniden denenebilir."
)


@functools.singledispatch
def temsil_metni(kart: object) -> str:
    raise TypeError(f"Embedding'i olmayan tür: {type(kart).__name__}")


@temsil_metni.register
def _(kart: YetenekKarti) -> str:
    """`kart.somut_ciktilar` yüklenmiş olmalı."""
    return yetenek_temsil_metni(
        rol_alani=kart.rol_alani,
        deneyim_seviyesi=kart.deneyim_seviyesi,
        sektor_ilgi_alani=kart.sektor_ilgi_alani,
        araclar_teknolojiler=kart.araclar_teknolojiler,
        somut_ciktilar=[(c.baslik, is_kalemi_metni(c)) for c in kart.somut_ciktilar],
    )


@temsil_metni.register
def _(kart: IhtiyacKarti) -> str:
    return ihtiyac_temsil_metni(
        problem_tanimi=kart.problem_tanimi, basari_kriteri=kart.basari_kriteri
    )


@temsil_metni.register
def _(kart: FirmaKarti) -> str:
    """Firmanın ne yaptığını temsil eder; `kart.kurum` yüklenmiş olmalı (sektör)."""
    return firma_temsil_metni(
        ne_yapiyoruz=kart.ne_yapiyoruz,
        yetkinlikler=kart.yetkinlikler,
        onceki_isler=kart.onceki_isler,
        sektor=kart.kurum.sektor,
    )


async def embedding_hesapla(oturum: AsyncSession, kart: Kart) -> bool:
    """Kartın embedding'ini hesaplayıp kaydeder; Voyage'a ulaşılamazsa False."""
    metin = temsil_metni(kart)
    try:
        kart.embedding = await embedding_uret(metin, girdi_turu="document")
    except EmbeddingHatasi:
        logger.warning(
            "%s embedding'i hesaplanamadı (%s)", type(kart).__name__, kart.id, exc_info=True
        )
        return False
    await oturum.commit()
    return True
