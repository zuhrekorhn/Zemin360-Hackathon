"""C2PA içerik kimlik bilgisinin okunması (plan § 4.3; `c2pa-python`).

Varsa üretim aracı ve düzenleme eylemleri kaydedilir; yoksa hiçbir sonuç
çıkarılmaz (çoğu dosyada yoktur). Seviyeyi etkilemez: bilgi kanıt satırında
gösterilir ve GİRVAK incelemesine bağlam olur. Ham dosyadan, yeniden kodlamadan
önce okunur (yeniden kodlama manifestoyu siler).
"""

from __future__ import annotations

import io
import json
from typing import Any

from app.core.dosya_hatti import on_okuyucu

AZAMI_EYLEM = 10


def c2pa_ozeti(manifest_deposu: dict[str, Any]) -> dict[str, Any] | None:
    """Etkin manifestodan üretim aracı, eylemler, imzalayan ve geçerlilik."""
    etkin = manifest_deposu.get("active_manifest")
    manifesto = (manifest_deposu.get("manifests") or {}).get(etkin) if etkin else None
    if not isinstance(manifesto, dict):
        return None
    arac = manifesto.get("claim_generator")
    bilgi = manifesto.get("claim_generator_info")
    if not arac and isinstance(bilgi, list) and bilgi and isinstance(bilgi[0], dict):
        arac = " ".join(str(bilgi[0].get(k, "")) for k in ("name", "version")).strip()
    eylemler: list[str] = []
    for iddia in manifesto.get("assertions", []):
        if str(iddia.get("label", "")).startswith("c2pa.actions"):
            for eylem in (iddia.get("data") or {}).get("actions", []):
                ad = str(eylem.get("action", "")).removeprefix("c2pa.")
                if ad and ad not in eylemler:
                    eylemler.append(ad)
    imza = manifesto.get("signature_info") or {}
    return {
        "arac": (str(arac)[:120] if arac else None),
        "eylemler": eylemler[:AZAMI_EYLEM],
        "imzalayan": imza.get("issuer"),
        "gecerli": not manifest_deposu.get("validation_status"),
    }


@on_okuyucu("c2pa")
def c2pa_oku(ham: bytes, icerik_turu: str) -> dict[str, Any] | None:
    import c2pa

    try:
        with c2pa.Reader(icerik_turu, io.BytesIO(ham)) as okuyucu:
            return c2pa_ozeti(json.loads(okuyucu.json()))
    except c2pa.C2paError:
        return None  # manifesto yok (dosyaların çoğu)
