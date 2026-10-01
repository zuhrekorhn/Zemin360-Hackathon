"""Kanıt adresinin okunması ve değerlendirmeye hazırlanması (plan § 5).

Okuyucu zinciri (`app/core/kanit_okuma/`) belgeyi verir; burada çekirdeğin
girdisine (`OkunanKanit`) çevrilir ve uzun metinde modelin göreceği parçalar
iddiaya göre seçilir (§ 5.4). Alıntı denetimi yine tam metne yapılır.
Herkese açık okunan çalışma seviye C'dir; bağlı hesap (B) adım 8'de.
"""

from __future__ import annotations

import httpx

from app.agents.dogrulama.kurallar import OkunanKanit
from app.core.embeddings import embedding_listesi_uret
from app.core.kanit_okuma import kaniti_oku
from app.core.kanit_okuma.belge import KaynakSeviyesi
from app.core.kanit_okuma.parca_secimi import Gomucu, sec


async def kanit_oku(
    url: str,
    iddia_sorgulari: list[str],
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    gom: Gomucu = embedding_listesi_uret,
) -> OkunanKanit:
    belge = await kaniti_oku(url, transport=transport)
    model_metni = await sec(belge.metin, iddia_sorgulari, gom) if belge.metin else ""
    return OkunanKanit(
        erisim=belge.erisim,
        seviye=KaynakSeviyesi.KAMUYA_ACIK,
        metin=belge.metin,
        url=url,
        platform=belge.platform,
        model_metni=model_metni,
    )
