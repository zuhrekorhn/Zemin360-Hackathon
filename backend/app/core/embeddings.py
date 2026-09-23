"""Embedding üretimi — Voyage AI (voyage-4, 1024 boyut).

docs/matching-algorithm.md § 1-2. Kart onaylandığında ve her güncellemede
(versiyon arttığında) çağrılır. Tanımlama Ajanı ihtiyaç kartı için aynı
`embedding_uret` fonksiyonunu kullanır, sadece temsil metni şablonu farklıdır.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import httpx

from app.core.config import get_settings
from app.db.base import EMBEDDING_DIM

VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"

# Voyage, arama tarafıyla belge tarafını ayrı kodluyor. Kartlar "document",
# eşleştirmede karşıya sorulan metin "query" olarak gönderilir.
GirdiTuru = Literal["document", "query"]


class EmbeddingHatasi(RuntimeError):
    """Voyage çağrısı başarısız oldu ya da beklenmeyen bir yanıt döndü."""


async def embedding_uret(metin: str, girdi_turu: GirdiTuru = "document") -> list[float]:
    """Tek bir metni vektöre çevirir.

    Hata durumunda `EmbeddingHatasi` fırlatır — sessizce boş vektör dönmez,
    çünkü embedding'i olmayan kart eşleştirmeye hiç girmez.
    """
    ayarlar = get_settings()
    if not ayarlar.voyage_api_key:
        raise EmbeddingHatasi("VOYAGE_API_KEY tanımlı değil (.env)")

    govde = {
        "input": [metin],
        "model": ayarlar.voyage_model,
        "input_type": girdi_turu,
        "output_dimension": EMBEDDING_DIM,
    }

    async with httpx.AsyncClient(timeout=30) as istemci:
        yanit = await istemci.post(
            VOYAGE_URL,
            json=govde,
            headers={"Authorization": f"Bearer {ayarlar.voyage_api_key}"},
        )

    if yanit.status_code != 200:
        raise EmbeddingHatasi(f"Voyage {yanit.status_code}: {yanit.text[:300]}")

    try:
        vektor = yanit.json()["data"][0]["embedding"]
    except (KeyError, IndexError, ValueError) as hata:
        raise EmbeddingHatasi(f"Voyage yanıtı okunamadı: {yanit.text[:300]}") from hata

    if len(vektor) != EMBEDDING_DIM:
        raise EmbeddingHatasi(f"Beklenen boyut {EMBEDDING_DIM}, gelen {len(vektor)}")

    return vektor


def yetenek_temsil_metni(
    *,
    rol_alani: str,
    deneyim_seviyesi: str,
    sektor_ilgi_alani: Sequence[str],
    araclar_teknolojiler: Sequence[str],
    somut_ciktilar: Sequence[tuple[str, str | None]] = (),
) -> str:
    """Yetenek kartını embedding'e verilecek düz metne çevirir.

    Şablon docs/matching-algorithm.md § 1'den birebir alındı — değiştirilirse
    mevcut tüm vektörlerin yeniden hesaplanması gerekir.
    """
    ciktilar = "; ".join(
        baslik if not aciklama else f"{baslik}: {aciklama}" for baslik, aciklama in somut_ciktilar
    )
    return "\n".join(
        [
            f"Rol: {rol_alani}",
            f"Deneyim: {deneyim_seviyesi}",
            f"Sektör ilgisi: {', '.join(sektor_ilgi_alani)}",
            f"Araçlar: {', '.join(araclar_teknolojiler)}",
            f"Öne çıkan çıktılar: {ciktilar}",
        ]
    )
