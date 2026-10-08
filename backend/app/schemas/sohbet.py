"""İki sohbet ajanının paylaştığı istek şemaları.

Keşif ve Tanımlama aynı motoru kullanıyor (docs/agent-specs.md § 2), sohbet
istekleri de aynı biçimde.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

# Sohbette tek cevabın üst sınırı. Her turda bütün geçmiş modele yeniden gidiyor;
# yapıştırılan çok uzun bir metin her tur maliyeti katlar ve bağlam sınırına çarpar.
CEVAP_EN_COK = 6000


class SohbetBaslatIstegi(BaseModel):
    """Gövde boş: oturum sunucuda açılır, sahibi token'daki hesaptır."""


class SohbetCevapIstegi(BaseModel):
    oturum_id: uuid.UUID
    cevap: str = Field(min_length=1, max_length=CEVAP_EN_COK)
