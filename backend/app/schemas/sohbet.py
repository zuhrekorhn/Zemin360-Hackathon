"""İki sohbet ajanının paylaştığı istek şemaları.

Keşif ve Tanımlama aynı motoru kullanıyor (docs/agent-specs.md § 2), sohbet
istekleri de aynı biçimde.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# Boşluktan ibaret olmayan metin. Onaydaki ad alanı için: kayıt e-postayla
# upsert ediliyor ve boş ad yeni kayıtta NOT NULL'a takılırdı; 422 daha net.
DoluMetin = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SohbetBaslatIstegi(BaseModel):
    """Gövde boş: oturum sunucuda açılır, sahibi token'daki hesaptır."""


class SohbetCevapIstegi(BaseModel):
    oturum_id: uuid.UUID
    cevap: str = Field(min_length=1)
