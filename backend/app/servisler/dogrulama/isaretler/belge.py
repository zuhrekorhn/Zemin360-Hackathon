"""Belge tutarsız (plan § 9): `belge_tutarsiz`.

Yükleme anında, çapalar doğrulandıktan sonra: bozuk e-imza ya da gencin adının
geçmediği doğrulama sayfası. Kural saf (`agents/dogrulama/capalar.belge_tutarsizliklari`);
seviye zaten çapadan hesaplanır (bozuk imza D), işaret puanı ayrıca değiştirmez (İ1).
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dogrulama.capalar import belge_tutarsizliklari
from app.models.inceleme_isareti import TUR_BELGE_TUTARSIZ
from app.models.kanit_parcasi import KanitParcasi
from app.models.somut_cikti import SomutCikti
from app.servisler import inceleme


async def belge_tutarliligi(
    oturum: AsyncSession, parca: KanitParcasi, cikti: SomutCikti, kullanici_id: uuid.UUID
) -> None:
    bulgular = belge_tutarsizliklari((parca.belge or {}).get("capalar", []))
    if not bulgular:
        return
    await oturum.flush()  # parçanın kimliği sinyale yazılır
    await inceleme.sinyal_ekle(
        oturum,
        TUR_BELGE_TUTARSIZ,
        kullanici_id,
        cikti.id,
        "bulgular",
        [
            {
                "anahtar": f"{parca.id}:{b['neden']}:{b.get('adres') or ''}",
                "parca_id": str(parca.id),
                "dosya_adi": parca.dosya_adi,
                **b,
            }
            for b in bulgular
        ],
    )
