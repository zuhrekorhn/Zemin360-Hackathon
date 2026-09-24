"""İki sohbet ajanının paylaştığı istek şemaları.

Keşif ve Tanımlama aynı motoru kullanıyor (docs/agent-specs.md § 2), sohbet
istekleri de aynı biçimde.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class SohbetBaslatIstegi(BaseModel):
    """Şimdilik gövde boş — oturum sunucuda açılır. Auth Faz 3'te gelecek."""


class SohbetCevapIstegi(BaseModel):
    oturum_id: uuid.UUID
    cevap: str = Field(min_length=1)
