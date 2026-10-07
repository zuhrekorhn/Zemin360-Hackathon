"""Kanıt iddiayla çelişiyor (docs/dogrulama.md § 9, § 11.2): `kanit_celisiyor`.

Model "çelişiyor" dedi VE alıntısı kanıtın tam metninde bulundu (çekirdek,
alıntısız çelişkiyi zaten atar). Puan tarafı çekirdekte: ilgili başlık en çok
1. Bu işaret puana ikinci kez dokunmaz (İ1); GİRVAK'ın görmesi içindir.

Aynı parça + iddia + alıntı bir kez kuyruğa düşer: itiraz ya da yeniden
değerlendirme aynı çelişkiyi yeniden üretirse GİRVAK'a tekrar gitmez.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dogrulama.alinti import normallestir
from app.models.inceleme_isareti import TUR_KANIT_CELISIYOR
from app.models.kanit_parcasi import KanitParcasi
from app.models.somut_cikti import SomutCikti
from app.servisler import inceleme


def celiski_sinyalleri(
    parcalar: Sequence[KanitParcasi], parca_celiskileri: Sequence[Sequence[dict]]
) -> list[dict[str, Any]]:
    return [
        {
            "anahtar": f"{parca.id}:{celiski['iddia']}:{normallestir(celiski.get('alinti') or '')}",
            "parca_id": str(parca.id),
            "adres": parca.url,
            "dosya_adi": parca.dosya_adi,
            "iddia": celiski["iddia"],
            "alinti": celiski.get("alinti"),
        }
        for parca, celiskiler in zip(parcalar, parca_celiskileri, strict=False)
        for celiski in celiskiler
    ]


async def celiskili_kanit(
    oturum: AsyncSession,
    cikti: SomutCikti,
    kullanici_id: uuid.UUID,
    parcalar: Sequence[KanitParcasi],
    parca_celiskileri: Sequence[Sequence[dict]],
) -> None:
    sinyaller = celiski_sinyalleri(parcalar, parca_celiskileri)
    if sinyaller:
        await inceleme.sinyal_ekle(
            oturum, TUR_KANIT_CELISIYOR, kullanici_id, cikti.id, "celiskiler", sinyaller
        )
