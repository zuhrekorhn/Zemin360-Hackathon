"""Kötüye kullanım sinyalleri (docs/dogrulama.md § 9): sinyali gören kod işareti açar, karar
GİRVAK'ın.

İşaretler puanı kendiliğinden değiştirmez (İ1). Her sinyal kendi modülünde;
değerlendirmeden sonra çalışanlar burada tek yerden çağrılır (`kanit.uygula`).
Yükleme anındaki sinyaller (belge tekilliği…) dosya servisinden çağrılır.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kanit_parcasi import KanitParcasi
from app.models.somut_cikti import SomutCikti
from app.servisler.dogrulama.isaretler.celiski import celiskili_kanit
from app.servisler.dogrulama.isaretler.tekrar import tekrar_eden_kanit


async def degerlendirme_isaretleri(
    oturum: AsyncSession,
    cikti: SomutCikti,
    kullanici_id: uuid.UUID,
    parcalar: Sequence[KanitParcasi] = (),
    parca_celiskileri: Sequence[Sequence[dict]] = (),
) -> None:
    """Değerlendirme yazıldıktan sonra (sahiplik ve çelişkiler okunmuşken).
    `parcalar` ve `parca_celiskileri` aynı sırada (çekirdeğin `okunanlar` sırası)."""
    await tekrar_eden_kanit(oturum, cikti, kullanici_id)
    await celiskili_kanit(oturum, cikti, kullanici_id, parcalar, parca_celiskileri)


__all__ = ["degerlendirme_isaretleri"]
