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

# Voyage, arama tarafıyla belge tarafını ayrı kodluyor ("document" / "query").
# Bugün BÜTÜN kartlar (yetenek, firma ve ihtiyaç) "document" olarak gönderiliyor;
# "query" kullanılmıyor. Ölçüm: ihtiyacı "query" göndermek benzerlikleri ~0.10
# aşağı çekiyor, bu yüzden benzerlik tabanı (eslestirme.BENZERLIK_ALT_SINIRI)
# birlikte yeniden kalibre edilmeden geçiş yapılmamalı
# (docs/matching-algorithm.md § Bilinen sınırlar).
GirdiTuru = Literal["document", "query"]


class EmbeddingHatasi(RuntimeError):
    """Voyage çağrısı başarısız oldu ya da beklenmeyen bir yanıt döndü."""


async def embedding_uret(metin: str, girdi_turu: GirdiTuru = "document") -> list[float]:
    """Tek bir metni vektöre çevirir.

    Hata durumunda `EmbeddingHatasi` fırlatır — sessizce boş vektör dönmez,
    çünkü embedding'i olmayan kart eşleştirmeye hiç girmez.
    """
    return (await embedding_listesi_uret([metin], girdi_turu))[0]


async def embedding_listesi_uret(
    metinler: list[str], girdi_turu: GirdiTuru = "document"
) -> list[list[float]]:
    """Birden çok metni tek istekte vektörlere çevirir (sıra korunur).

    Uzun kanıt metninin parçaları için (docs/plans/dogrulama-iyilestirme.md § 5.4).
    """
    ayarlar = get_settings()
    if not ayarlar.voyage_api_key:
        raise EmbeddingHatasi("VOYAGE_API_KEY tanımlı değil (.env)")

    govde = {
        "input": metinler,
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
        veriler = sorted(yanit.json()["data"], key=lambda d: d["index"])
        vektorler = [d["embedding"] for d in veriler]
    except (KeyError, IndexError, ValueError, TypeError) as hata:
        raise EmbeddingHatasi(f"Voyage yanıtı okunamadı: {yanit.text[:300]}") from hata

    if len(vektorler) != len(metinler) or any(len(v) != EMBEDDING_DIM for v in vektorler):
        raise EmbeddingHatasi(f"Beklenen {len(metinler)} × {EMBEDDING_DIM} vektör gelmedi")
    return vektorler


def ihtiyac_temsil_metni(*, problem_tanimi: str, basari_kriteri: str | None) -> str:
    """İhtiyaç kartını embedding'e verilecek düz metne çevirir.

    Şablon docs/matching-algorithm.md § 1'den birebir alındı — kısıtlar ve
    tercih alanları bilinçli olarak DIŞARIDA: onlar sert filtre adımında
    SQL ile çalışıyor, benzerlik metnini bulandırmamalı.
    """
    satirlar = [f"Problem: {problem_tanimi}"]
    # Boş kriter satırı yazılmaz: içeriksiz başlık benzerliği bulandırıyordu.
    if basari_kriteri:
        satirlar.append(f"Başarı kriteri: {basari_kriteri}")
    return "\n".join(satirlar)


def firma_temsil_metni(
    *,
    ne_yapiyoruz: str,
    yetkinlikler: Sequence[str],
    onceki_isler: str | None,
    sektor: str | None,
) -> str:
    """Firma kartını embedding'e verilecek düz metne çevirir (docs/plans/firma-akisi.md § 4).

    Firmanın **ne yaptığı**: iş birliği ortağı arayan ilanın problemiyle
    karşılaştırılır. Aradığı ortak ve iş birliği türü bilinçli olarak DIŞARIDA
    (onlar firmanın ne yaptığını değil, ne istediğini söylüyor). Değiştirilirse
    mevcut firma vektörleri yeniden hesaplanmalı.
    """
    return "\n".join(
        [
            f"Firma ne yapıyor: {ne_yapiyoruz}",
            f"Yetkinlikler: {', '.join(yetkinlikler)}",
            f"Önceki işler: {onceki_isler or ''}",
            f"Sektör: {sektor or ''}",
        ]
    )


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
