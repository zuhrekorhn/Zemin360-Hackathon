"""Referans isteklerinin orkestrasyonu: yanıt, zaman aşımı, yeniden isteme.

Kurallar `app/agents/dogrulama/` (durum makinesi, puan çevrimi, geçerlilik);
burada modele uygulanmaları. Commit çağıranın işi.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dogrulama import (
    DURUM_BEKLIYOR,
    OLAY_YANIT,
    OLAY_ZAMAN_ASIMI,
    ReferansYaniti,
    gecerli_referans_puanlari,
    referans_gecerli_mi,
    referans_gecisi,
    referans_yeniden_istenebilir_mi,
    ucuncu_taraf_onayi_hesapla,
    zaman_asimina_ugradi_mi,
)
from app.api.bildirimler import bildirim_ekle
from app.models.bildirim import TUR_REFERANS_YANITI
from app.models.guven_skoru import GuvenSkoru
from app.models.referans_istegi import ReferansIstegi
from app.models.somut_cikti import SomutCikti
from app.servisler.dogrulama.sorgular import cikti_getir, gencin_hesap_id


class ReferansYenidenIstenemez(Exception):
    """Yeniden isteme bu istek için anlamlı değil. Mesaj kullanıcıya gösterilir (409)."""


def referans_guncel_mi(cikti: SomutCikti, referans: ReferansIstegi) -> bool:
    """Bu referans yanıtı iş kaleminin güncel hâli için mi? (genc-akisi § 0, karar 8)"""
    return referans_gecerli_mi(referans.yanit_tarihi, cikti.icerik_tarihi)


def ucuncu_taraf_puani(cikti: SomutCikti) -> int | None:
    """Yalnızca güncel referans yanıtlarından; iş değiştiyse eski yanıtlar girmez.
    Güncel yanıt yoksa None ("—").

    `cikti.referans_istekleri` yüklenmiş olmalı.
    """
    yanitlar = [
        ReferansYaniti(puan=r.puan, yanit_tarihi=r.yanit_tarihi) for r in cikti.referans_istekleri
    ]
    return ucuncu_taraf_onayi_hesapla(gecerli_referans_puanlari(yanitlar, cikti.icerik_tarihi))


def zaman_asimini_isle(referans: ReferansIstegi, simdi: dt.datetime | None = None) -> bool:
    """Süresi dolmuşsa `yanit_yok`'a geçirir; kaydedilecek değişiklik varsa True.

    Zamanlayıcı yok (bilinçli): geçiş, kayda her dokunulduğunda hesaplanıyor.
    """
    if not zaman_asimina_ugradi_mi(referans.olusturma_tarihi, referans.durum, simdi):
        return False
    referans.durum = referans_gecisi(referans.durum, OLAY_ZAMAN_ASIMI)
    return True


def zaman_asimlarini_isle(
    referanslar: Iterable[ReferansIstegi], simdi: dt.datetime | None = None
) -> bool:
    """Birden çok istek için `zaman_asimini_isle`; herhangi biri geçtiyse True.

    Liste bilerek önce kuruluyor: `any` kısa devre yapıp kalan istekleri atlamasın.
    """
    return any([zaman_asimini_isle(r, simdi) for r in referanslar])


async def referans_yanitla(
    oturum: AsyncSession, referans: ReferansIstegi, *, puan: int, yorum: str | None
) -> SomutCikti:
    """Referansın yanıtını yazar, üçüncü taraf onayını günceller, gence bildirir.

    Geçersiz geçişte (zaten yanıtlanmış, süresi dolmuş) `GecersizReferansGecisi`.
    Zaman aşımını çağıran önce işler: GET ve POST aynı kuralı uygulasın diye.
    """
    referans.durum = referans_gecisi(referans.durum, OLAY_YANIT)
    referans.yanit_metni = yorum
    referans.puan = puan
    referans.yanit_tarihi = dt.datetime.now(dt.UTC)

    cikti = await cikti_getir(oturum, referans.somut_cikti_id)
    if cikti.guven_skoru is None:
        # Kanıt değerlendirilmeden referans gelirse yalnızca Referans başlığı
        # dolar; Kanıt, Sonuç ve Rol "—" kalır. Eskiden 0 yazılıyordu: hiç
        # değerlendirilmemiş başlıklar 0/3 görünüyor, Eşleştirme'ye "sonuç
        # belirtilmemiş" diye gidiyor ve uyum bonusunu düşürüyordu (bulgu 17).
        cikti.guven_skoru = GuvenSkoru()
    # Birden fazla referans yanıtlamış olabilir; son gelen öncekini ezmesin.
    # İş kalemi sonradan değiştiyse, değişiklikten önceki yanıtlar sayılmaz.
    cikti.guven_skoru.ucuncu_taraf_onayi = ucuncu_taraf_puani(cikti)
    bildirim_ekle(
        oturum,
        await gencin_hesap_id(oturum, cikti.yetenek_karti_id),
        TUR_REFERANS_YANITI,
        "Bir referansın yanıt verdi; güven göstergen güncellendi.",
    )
    return cikti


def referans_iste(cikti: SomutCikti, referans_email: str) -> ReferansIstegi:
    """Yeni referans isteği açar. Göstergeye dokunmaz, model çağrılmaz (bulgu 16):
    referans eklemek Kanıt, Sonuç ve Rol'ü yeniden hesaplatmaz."""
    istek = ReferansIstegi(referans_email=referans_email)
    cikti.referans_istekleri.append(istek)
    return istek


def yeniden_isteme_engeli(cikti: SomutCikti, referans: ReferansIstegi) -> str | None:
    """Bu istek yeniden istenebilir mi? Değilse nedeni (kural:
    `referans_yeniden_istenebilir_mi`). Uç ve arayüz düğmesi aynı yanıtı kullanır."""
    return referans_yeniden_istenebilir_mi(
        durum=referans.durum,
        guncel=referans_guncel_mi(cikti, referans),
        ayni_kisiden_bekleyen_var=any(
            r.id != referans.id
            and r.referans_email == referans.referans_email
            and r.durum == DURUM_BEKLIYOR
            for r in cikti.referans_istekleri
        ),
    )


def referansi_yeniden_iste(cikti: SomutCikti, referans: ReferansIstegi) -> ReferansIstegi:
    """Aynı kişiye yeni istek (yeni token); eski yanıt geçmiş olarak kalır.

    Anlamlı değilse `ReferansYenidenIstenemez`. Rubrik yeniden çalışmaz.
    """
    zaman_asimini_isle(referans)
    engel = yeniden_isteme_engeli(cikti, referans)
    if engel:
        raise ReferansYenidenIstenemez(engel)
    yeni = ReferansIstegi(referans_email=referans.referans_email)
    cikti.referans_istekleri.append(yeni)
    return yeni
