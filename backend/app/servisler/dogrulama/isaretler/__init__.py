"""Kötüye kullanım sinyalleri (plan § 9): sinyali gören kod işareti açar, karar GİRVAK'ın.

İşaretler puanı kendiliğinden değiştirmez (İ1). Her sinyal kendi modülünde;
değerlendirmeden sonra çalışanlar burada tek yerden çağrılır (`kanit.uygula`).
Yükleme anındaki sinyaller (belge tekilliği…) dosya servisinden çağrılır.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.somut_cikti import SomutCikti
from app.servisler.dogrulama.isaretler.tekrar import tekrar_eden_kanit


async def degerlendirme_isaretleri(
    oturum: AsyncSession, cikti: SomutCikti, kullanici_id: uuid.UUID
) -> None:
    """Değerlendirme yazıldıktan sonra (sahiplik ve çelişkiler okunmuşken)."""
    await tekrar_eden_kanit(oturum, cikti, kullanici_id)


__all__ = ["degerlendirme_isaretleri"]
