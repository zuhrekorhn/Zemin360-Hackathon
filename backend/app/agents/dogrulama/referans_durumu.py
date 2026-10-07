"""Referans isteğinin durumları ve zaman aşımı (docs/agent-specs.md § 4.2).

Zaman aşımı bir ceza değil, nötr bir durumdur (docs/sequence-diagrams.md
§ Akış 2, else dalı). Ayrı bir zamanlayıcı yok: geçiş okuma anında hesaplanır.
"""

from __future__ import annotations

import datetime as dt

# Referans yanıtı için tanınan süre (docs/agent-specs.md § 4.2: 5-7 gün).
# Üst sınır seçildi: erken "yanıt yok" demek referans kişiyi cezalandırır.
REFERANS_TIMEOUT_GUN = 7
# Tek hatırlatma e-postası bu günde gider (docs/dogrulama.md § 7; Canlılık taraması).
HATIRLATMA_GUN = 3

DURUM_BEKLIYOR = "bekliyor"
# "onaylandi" değil: referans olumsuz de yanıtlayabilir, durum yalnızca
# yanıtın geldiğini söyler. Değerlendirme ucuncu_taraf_onayi puanında.
DURUM_YANITLANDI = "yanitlandi"
DURUM_YANIT_YOK = "yanit_yok"
# Genç isteği geri çekti (ör. yanlış adres); link artık form açmaz.
DURUM_GERI_CEKILDI = "geri_cekildi"


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


def hatirlatma_zamani_mi(
    olusturma_tarihi: dt.datetime,
    durum: str,
    hatirlatma_tarihi: dt.datetime | None,
    simdi: dt.datetime | None = None,
) -> bool:
    """Bekleyen istek için tek hatırlatmanın zamanı geldi mi? (3. gün, bir kez;
    süresi dolmuşsa hatırlatma değil zaman aşımı.)"""
    if durum != DURUM_BEKLIYOR or hatirlatma_tarihi is not None:
        return False
    an = simdi or dt.datetime.now(dt.UTC)
    if olusturma_tarihi.tzinfo is None:
        olusturma_tarihi = olusturma_tarihi.replace(tzinfo=dt.UTC)
    gecen = an - olusturma_tarihi
    return dt.timedelta(days=HATIRLATMA_GUN) <= gecen < dt.timedelta(days=REFERANS_TIMEOUT_GUN)


# --- Durum makinesi ------------------------------------------------------------------------
# Eşleşme (app/agents/eslesme_durumu.py) ve takip durum makineleriyle aynı desen:
# geçiş kuralı tek yerde ve saf; uçlar ve servisler yalnızca söyleneni uygular.
#
#     bekliyor ──yanit──────▶ yanitlandi
#        ├─────zaman_asimi──▶ yanit_yok      (okuma anında, nötr; ceza değil)
#        └─────geri_cek─────▶ geri_cekildi   (genç; ör. yanlış adres)

OLAY_YANIT = "yanit"
OLAY_ZAMAN_ASIMI = "zaman_asimi"
OLAY_GERI_CEK = "geri_cek"

# (olay, kaynak durum) → hedef durum
GECISLER: dict[tuple[str, str], str] = {
    (OLAY_YANIT, DURUM_BEKLIYOR): DURUM_YANITLANDI,
    (OLAY_ZAMAN_ASIMI, DURUM_BEKLIYOR): DURUM_YANIT_YOK,
    (OLAY_GERI_CEK, DURUM_BEKLIYOR): DURUM_GERI_CEKILDI,
}

# 409 cümleleri referans kişinin sayfasında görünür (docs/icerik-rehberi.md).
_GECERSIZ_GECIS_CUMLELERI: dict[tuple[str, str], str] = {
    (OLAY_YANIT, DURUM_YANITLANDI): "Bu referans zaten yanıtlanmış",
    (OLAY_YANIT, DURUM_YANIT_YOK): "Bu referans isteğinin süresi doldu, yanıt alınamıyor.",
    (OLAY_YANIT, DURUM_GERI_CEKILDI): "Bu referans isteği geri çekildi, yanıt alınamıyor.",
    (OLAY_GERI_CEK, DURUM_YANITLANDI): "Bu referans yanıt verdi; yanıt geri çekilemez.",
    (OLAY_GERI_CEK, DURUM_YANIT_YOK): "Bu isteğin süresi zaten doldu.",
}


class GecersizReferansGecisi(Exception):
    """Tablo dışı geçiş. Mesaj kullanıcıya olduğu gibi gösterilebilir (uçta 409)."""

    def __init__(self, durum: str, olay: str) -> None:
        self.durum, self.olay = durum, olay
        super().__init__(
            _GECERSIZ_GECIS_CUMLELERI.get(
                (olay, durum), "Bu referans isteği artık bu işlemi kabul etmiyor."
            )
        )


def referans_gecisi(durum: str, olay: str) -> str:
    """Olayın götürdüğü durum; tablo dışıysa `GecersizReferansGecisi`."""
    hedef = GECISLER.get((olay, durum))
    if hedef is None:
        raise GecersizReferansGecisi(durum, olay)
    return hedef


def yanitlanabilir_mi(durum: str) -> bool:
    """Referans kişinin sayfası formu gösterecek mi? (GET ve POST aynı kural.)"""
    return (OLAY_YANIT, durum) in GECISLER
