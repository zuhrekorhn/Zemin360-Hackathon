"""Referans isteğinin durumları ve zaman aşımı (docs/agent-specs.md § 4.2).

Zaman aşımı bir ceza değil, nötr bir durumdur (docs/sequence-diagrams.md
§ Akış 2, else dalı). Ayrı bir zamanlayıcı yok: geçiş okuma anında hesaplanır.
"""

from __future__ import annotations

import datetime as dt

# Referans yanıtı için tanınan süre (docs/agent-specs.md § 4.2: 5-7 gün).
# Üst sınır seçildi: erken "yanıt yok" demek referans kişiyi cezalandırır.
REFERANS_TIMEOUT_GUN = 7

DURUM_BEKLIYOR = "bekliyor"
# "onaylandi" değil: referans olumsuz de yanıtlayabilir, durum yalnızca
# yanıtın geldiğini söyler. Değerlendirme ucuncu_taraf_onayi puanında.
DURUM_YANITLANDI = "yanitlandi"
DURUM_YANIT_YOK = "yanit_yok"


def zaman_asimina_ugradi_mi(
    olusturma_tarihi: dt.datetime, durum: str, simdi: dt.datetime | None = None
) -> bool:
    """Bekleyen bir referans isteği süresini doldurmuş mu?

    Ayrı bir zamanlayıcı yok (bkz. Eşleştirme'deki aynı karar): bu geçiş
    okuma anında hesaplanıyor.
    """
    if durum != DURUM_BEKLIYOR:
        return False
    an = simdi or dt.datetime.now(dt.UTC)
    if olusturma_tarihi.tzinfo is None:
        olusturma_tarihi = olusturma_tarihi.replace(tzinfo=dt.UTC)
    return an - olusturma_tarihi >= dt.timedelta(days=REFERANS_TIMEOUT_GUN)
