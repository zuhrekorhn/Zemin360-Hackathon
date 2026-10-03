"""Belge tekilliği (plan § 4.2, § 9, bulgu 48): aynı doğrulama adresi (QR / sertifika /
rozet) ikinci bir hesapta kullanılırsa reddedilmez, `ayni_belge_iki_hesapta`
işaretiyle GİRVAK kuyruğuna düşer. İşaret puanı değiştirmez (İ1).

Karşılaştırma normalleştirilmiş adresle (`normal_adres`); arama JSONB içerme
sorgusuyla (`belge->'capalar' @> [{"normal_adres": …}]`).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inceleme_isareti import TUR_AYNI_BELGE_IKI_HESAPTA
from app.models.kanit_parcasi import KanitParcasi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler import inceleme


def _birlestir(eski: dict[str, Any], yeni: dict[str, Any]) -> dict[str, Any]:
    return {**eski, "eslesmeler": [*eski.get("eslesmeler", []), *yeni["eslesmeler"]]}


async def belge_tekilligi(
    oturum: AsyncSession, parca: KanitParcasi, cikti: SomutCikti, kullanici_id: uuid.UUID
) -> None:
    adresler = {
        c["normal_adres"] for c in (parca.belge or {}).get("capalar", []) if c.get("normal_adres")
    }
    eslesmeler = []
    for adres in sorted(adresler):
        diger = await oturum.execute(
            select(KanitParcasi.id, YetenekKarti.kullanici_id)
            .join(SomutCikti, SomutCikti.id == KanitParcasi.somut_cikti_id)
            .join(YetenekKarti, YetenekKarti.id == SomutCikti.yetenek_karti_id)
            .where(
                KanitParcasi.belge["capalar"].contains([{"normal_adres": adres}]),
                YetenekKarti.kullanici_id != kullanici_id,
            )
            .limit(5)
        )
        eslesmeler.extend(
            {"adres": adres, "diger_parca_id": str(p), "diger_kullanici_id": str(k)}
            for p, k in diger.all()
        )
    if not eslesmeler:
        return
    await inceleme.isaret_ac(
        oturum,
        TUR_AYNI_BELGE_IKI_HESAPTA,
        kullanici_id,
        somut_cikti_id=cikti.id,
        ayrinti={"eslesmeler": eslesmeler},
        birlestir=_birlestir,
    )
