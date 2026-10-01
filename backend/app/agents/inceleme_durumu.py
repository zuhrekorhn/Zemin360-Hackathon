"""GİRVAK inceleme işaretinin durumu (docs/plans/dogrulama-iyilestirme.md § 9).

Eşleşme, takip ve referans durum makineleriyle aynı desen: geçiş kuralı tek
yerde ve saf; servis yalnızca söyleneni uygular.

    acik ──kapandi────────▶ kapandi         ("sorun yok"; talepte "onaylandı")
      └────dogrulanamadi──▶ dogrulanamadi   (talepte "reddedildi")

Aynı kararın tekrarı yan etkisizdir (`None`). Kapanmış işarette başka karar
409: kararın yan etkisi (ör. ad değişikliği) geri alınmaz; GİRVAK yeni
bir işaretle yeniden bakar.
"""

from __future__ import annotations

ACIK = "acik"
KAPANDI = "kapandi"
DOGRULANAMADI = "dogrulanamadi"
DURUMLAR = (ACIK, KAPANDI, DOGRULANAMADI)
KARARLAR = (KAPANDI, DOGRULANAMADI)


class GecersizKarar(Exception):
    """Kapanmış işarete farklı karar. Mesaj GİRVAK'a gösterilir (uçta 409)."""


def inceleme_gecisi(durum: str, karar: str) -> str | None:
    """Kararın götürdüğü durum; aynı kararın tekrarıysa `None` (yan etkisiz)."""
    if karar not in KARARLAR:
        raise ValueError(f"Geçersiz karar: {karar}")
    if durum == ACIK:
        return karar
    if durum == karar:
        return None
    raise GecersizKarar("Bu işaret başka bir kararla kapandı; karar değiştirilemez.")
