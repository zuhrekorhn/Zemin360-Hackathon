"""Karşılıklı ilgiden sonra giden "eşleştiniz" e-postası (docs/plans/eposta-notlari.md § 3).

Yalnızca bildirimi alan tarafa gider (olayı yapan tarafın e-postaya ihtiyacı yok).
Gövdede karşı tarafın e-posta adresi olmaz: adres yalnızca sitede, `iletisim`
alanında iki tarafa açılır; e-postada iş birliği sayfasının bağlantısı vardır.
Hitap rehbere göre: gence "sen", firmaya "siz". Gönderim yanıttan sonra arka
planda; hata akışı düşürmez (İ9).
"""

from __future__ import annotations

from app.api.sahiplik import TARAF_ADAY, TARAF_ILAN, taraf_adi
from app.core.config import get_settings
from app.core.dis_servisler import kurulum
from app.core.dis_servisler.eposta import Eposta, dusmeden_gonder
from app.models.eslesme import Eslesme


def _alici_eposta(eslesme: Eslesme, alici_taraf: str) -> str | None:
    """Alıcının profildeki e-postası (sitede karşı tarafa açılanla aynı adres)."""
    if alici_taraf == TARAF_ADAY and eslesme.firma_karti is not None:
        return eslesme.firma_karti.kurum.iletisim_email
    if alici_taraf == TARAF_ADAY:
        return eslesme.yetenek_karti.kullanici.email
    return eslesme.ihtiyac_karti.kurum.iletisim_email


def eslesme_epostasi(eslesme: Eslesme, alici_taraf: str) -> Eposta | None:
    """E-postayı kurar; alıcının adresi ya da iş birliği yoksa `None` (gönderilmez).

    `eslesme` ilişkileriyle yüklenmiş olmalı (`iliskileriyle`) ve iş birliği açılmış.
    """
    adres = _alici_eposta(eslesme, alici_taraf)
    if not adres or eslesme.isbirligi is None:
        return None
    karsi_taraf = TARAF_ILAN if alici_taraf == TARAF_ADAY else TARAF_ADAY
    karsi = taraf_adi(eslesme, karsi_taraf)
    baglanti = f"{get_settings().uygulama_adresi.rstrip('/')}/isbirligi/{eslesme.isbirligi.id}"
    gence_mi = alici_taraf == TARAF_ADAY and eslesme.firma_karti is None
    if gence_mi:
        ad = taraf_adi(eslesme, TARAF_ADAY)
        metin = (
            f"Merhaba {ad},\n\n"
            f"Zemin360'ta {karsi} ile eşleştiniz: iki taraf da ilgisini gösterdi ve iş birliğiniz "
            "başladı. İletişim bilgileriniz iki tarafa açıldı; iş birliği sayfana buradan "
            f"ulaşabilirsin:\n{baglanti}"
        )
        konu = f"Zemin360: {karsi} ile eşleştin"
    else:
        metin = (
            "Merhaba,\n\n"
            f"Zemin360'ta {karsi} ile eşleştiniz: iki taraf da ilgisini gösterdi ve iş birliğiniz "
            "başladı. İletişim bilgileriniz iki tarafa açıldı; iş birliği sayfanıza buradan "
            f"ulaşabilirsiniz:\n{baglanti}"
        )
        konu = f"Zemin360: {karsi} ile eşleştiniz"
    return Eposta(alici=adres, konu=konu, metin=metin)


async def eposta_gonder(eposta: Eposta) -> None:
    """Arka plan işi: hata yutulur, akış sürer."""
    await dusmeden_gonder(kurulum.eposta_gonderici(), eposta)
