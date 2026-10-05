"""Zincirin yedek basamağı: tarayıcıyla okuma ve ekran görüntüsü kuralları (plan § 5.1, § 5.5).

Platform okuyucusu ya da genel okuyucu bir sonuç verdikten sonra çalışır:
  - Sonuç "engellendi" ya da "içerik yok" ise sayfa tarayıcıda yeniden açılır
    (bot engeli, JavaScript ile çizilen sayfa).
  - Görsel ağırlıklı platformda (Behance, Dribbble, ArtStation, portfolyo
    siteleri) sayfa açık okunsa bile ekran görüntüsü alınır: çalışma görseldir.
Giriş duvarı, "bulunamadı" ve "güvensiz" yedeğe gitmez (tarayıcı da aşamaz ya da
sonuç zaten kesindir). PDF dosya hattının işidir.

Kurallar saf (`yedek_gerekli_mi`, `ekran_kurali`, `birlestir`); ağ çağrısı
yalnızca `yedekle`'de.
"""

from __future__ import annotations

import dataclasses
import logging

import httpx

from app.core.dis_servisler.yedek_okuyucu import EkranKurali, TarayiciSayfasi, YedekOkuyucu
from app.core.kanit_okuma.belge import ErisimDurumu, KanitBelgesi
from app.core.kanit_okuma.erisim import EN_AZ_METIN
from app.core.kanit_okuma.istek import Sayfa
from app.core.kanit_okuma.okuyucular.genel import sayfadan_belge

logger = logging.getLogger("zemin360.kanit_okuma")

# Çalışmanın kendisi görsel olan platformlar (alan adı ve alt alan adları).
GORSEL_PLATFORMLAR = frozenset(
    {
        "behance.net",
        "dribbble.com",
        "artstation.com",
        "deviantart.com",
        "sketchfab.com",
        "grabcad.com",
        "pinterest.com",
        # Portfolyo kurucuları (kişisel portfolyo alan adları). Genel site kurucuları
        # (Wix, Squarespace) burada değil: oradaki metinsiz sayfa "metin azsa" kuralına düşer.
        "myportfolio.com",
        "carbonmade.com",
        "cargo.site",
        "format.com",
        "crevado.com",
        "pixpa.com",
    }
)

_YEDEKLENEN = frozenset({ErisimDurumu.ENGELLENDI, ErisimDurumu.ICERIK_YOK})


def gorsel_platform_mu(url: httpx.URL) -> bool:
    host = url.host.lower().removeprefix("www.")
    return any(host == alan or host.endswith(f".{alan}") for alan in GORSEL_PLATFORMLAR)


def yedek_gerekli_mi(url: httpx.URL, belge: KanitBelgesi) -> bool:
    if belge.platform == "pdf":
        return False
    if belge.erisim in _YEDEKLENEN:
        return True
    return belge.erisim is ErisimDurumu.ACIK and gorsel_platform_mu(url)


def ekran_kurali(url: httpx.URL) -> EkranKurali:
    """Görsel platformda her zaman; başka yerde yalnızca metin azsa (§ 5.5)."""
    return EkranKurali.HER_ZAMAN if gorsel_platform_mu(url) else EkranKurali.METIN_AZSA


def birlestir(url: str, onceki: KanitBelgesi, sayfa: TarayiciSayfasi) -> KanitBelgesi:
    """Tarayıcının okunuşunu önceki okunuşla birleştirir.

    Tarayıcı metni açık okuduysa onun okunuşu esas alınır (işlenmiş sayfa daha
    zengindir); okuyamadıysa (yine engel, yine boş) önceki açık okunuş korunur.
    Ekran görüntüsü yalnızca sayfa engel ya da giriş duvarı değilse eklenir:
    doğrulama ya da giriş sayfasının görüntüsü kanıt değildir. Okunuşta ne açık
    metin ne görüntü varsa önceki okunuş geçerlidir.
    """
    yeni = sayfadan_belge(
        url,
        Sayfa(sayfa.durum, sayfa.son_url, "text/html; charset=utf-8", sayfa.html.encode()),
        platform=onceki.platform,
    )
    goruntuler = (
        sayfa.ekran_goruntuleri
        if yeni.erisim in (ErisimDurumu.ACIK, ErisimDurumu.ICERIK_YOK)
        else ()
    )
    if yeni.erisim is ErisimDurumu.ACIK:
        temel = dataclasses.replace(
            yeni,
            hesaplar=onceki.hesaplar,
            veri=onceki.veri,
            platform_metni=onceki.platform_metni,
            yazarlar=yeni.yazarlar or onceki.yazarlar,
        )
    elif onceki.erisim is ErisimDurumu.ACIK or goruntuler:
        temel = onceki if onceki.erisim is ErisimDurumu.ACIK else yeni
    else:
        return onceki
    return dataclasses.replace(temel, ekran_goruntuleri=goruntuler)


async def yedekle(url: httpx.URL, belge: KanitBelgesi, yedek: YedekOkuyucu) -> KanitBelgesi:
    if not yedek_gerekli_mi(url, belge):
        return belge
    sayfa = await yedek.ac(str(url), ekran=ekran_kurali(url), en_az_metin=EN_AZ_METIN)
    if sayfa is None:
        return belge
    sonuc = birlestir(str(url), belge, sayfa)
    logger.info(
        "yedek okuyucu url_host=%s once=%s sonra=%s ekran=%d",
        url.host,
        belge.erisim.value,
        sonuc.erisim.value,
        len(sonuc.ekran_goruntuleri),
    )
    return sonuc
