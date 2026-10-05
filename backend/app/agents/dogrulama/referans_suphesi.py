"""Referans yanıtının şüphe sinyalleri (plan § 9 `referans_supheli`, bulgu 21). Saf.

Sinyal hüküm değildir: puanı değiştirmez (İ1), GİRVAK'ın bakması için kuyruğa
düşer. Sinyaller:
  - IP ya da tarayıcı özeti gencinkiyle aynı (gencin izleri: referans istediği
    anlardaki istek izleri);
  - form birkaç saniyede gönderildi (`HIZLI_YANIT_SN`), ya da hiç açılmadan;
  - aynı kişi (e-posta ya da IP özeti) çok sayıda gence yanıt verdi.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Collection

SINYAL_IP = "ip_genc_ile_ayni"
SINYAL_TARAYICI = "tarayici_genc_ile_ayni"
SINYAL_HIZLI = "hizli_yanit"
SINYAL_FORM_ACILMADAN = "form_acilmadan"
SINYAL_COK_GENC = "cok_gence_yanit"

# Dört soruluk formu okuyup doldurmak bundan kısa sürmez.
HIZLI_YANIT_SN = 20
# Bu kadar farklı gence yanıt veren aynı kişi (bu genç dahil)
COK_GENC_ESIGI = 3
# IP ve tarayıcı özetlerinin saklanma süresi (plan § 9)
IZ_SAKLAMA_GUN = 90


def referans_sinyalleri(
    *,
    yanit_ip: str | None,
    yanit_tarayici: str | None,
    genc_ipleri: Collection[str],
    genc_tarayicilari: Collection[str],
    form_acildi: bool,
    form_suresi_sn: float | None,
    genc_sayisi: int,
) -> tuple[str, ...]:
    sinyaller = []
    if yanit_ip and yanit_ip in genc_ipleri:
        sinyaller.append(SINYAL_IP)
    if yanit_tarayici and yanit_tarayici in genc_tarayicilari:
        sinyaller.append(SINYAL_TARAYICI)
    if not form_acildi:
        sinyaller.append(SINYAL_FORM_ACILMADAN)
    elif form_suresi_sn is not None and form_suresi_sn < HIZLI_YANIT_SN:
        sinyaller.append(SINYAL_HIZLI)
    if genc_sayisi >= COK_GENC_ESIGI:
        sinyaller.append(SINYAL_COK_GENC)
    return tuple(sinyaller)


def iz_saklama_siniri(simdi: dt.datetime) -> dt.datetime:
    """Bu tarihten önce açılmış isteklerin IP ve tarayıcı özetleri silinir."""
    return simdi - dt.timedelta(days=IZ_SAKLAMA_GUN)
