"""Zincirin yedek basamağı: tarayıcıyla okuma ve ekran görüntüsü kuralları (plan § 5.1, § 5.5).

Platform okuyucusu ya da genel okuyucu bir sonuç verdikten sonra çalışır:
  - Sonuç "engellendi" ya da "içerik yok" ise sayfa tarayıcıda yeniden açılır
    (bot engeli, JavaScript ile çizilen sayfa).
  - Görsel ağırlıklı platformda (Behance, Dribbble, ArtStation, portfolyo
    siteleri) sayfa açık okunsa bile ekran görüntüsü alınır: çalışma görseldir.
  - Tarayıcı da okuyamadıysa (servis yok, yine engel, yine boş ve görüntüsüz)
    ve bayrak açıksa üçüncü taraf servis (Jina Reader) denenir.
Kapalı platformlar (Instagram, LinkedIn, Facebook) yedeğe gitmez: tarayıcıda
açılsalar da içerik giriş penceresinin arkasındadır; okunamaz sayılır ve gence
alternatif yol sunulur (§ 18). Giriş duvarı, "bulunamadı" ve "güvensiz" yedeğe
gitmez (tarayıcı da aşamaz ya da sonuç zaten kesindir). PDF dosya hattının işidir.

Kurallar saf (`yedek_gerekli_mi`, `ekran_kurali`, `birlestir`); ağ çağrısı
yalnızca `yedekle`'de.
"""

from __future__ import annotations

import dataclasses
import logging

import httpx

from app.core.dis_servisler.uzak_okuyucu import UzakOkuyucu, UzakSayfa
from app.core.dis_servisler.yedek_okuyucu import EkranKurali, TarayiciSayfasi, YedekOkuyucu
from app.core.kanit_okuma.belge import ErisimDurumu, KanitBelgesi
from app.core.kanit_okuma.erisim import EN_AZ_METIN, erisim_durumu
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

KAPALI_PLATFORMLAR = frozenset({"instagram.com", "linkedin.com", "facebook.com"})

_YEDEKLENEN = frozenset({ErisimDurumu.ENGELLENDI, ErisimDurumu.ICERIK_YOK})


def _alanda_mi(url: httpx.URL, alanlar: frozenset[str]) -> bool:
    host = url.host.lower().removeprefix("www.")
    return any(host == alan or host.endswith(f".{alan}") for alan in alanlar)


def gorsel_platform_mu(url: httpx.URL) -> bool:
    return _alanda_mi(url, GORSEL_PLATFORMLAR)


def yedek_gerekli_mi(url: httpx.URL, belge: KanitBelgesi) -> bool:
    if belge.platform == "pdf" or _alanda_mi(url, KAPALI_PLATFORMLAR):
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


def uzak_birlestir(onceki: KanitBelgesi, sayfa: UzakSayfa) -> KanitBelgesi:
    """Üçüncü taraf servisin metni: açık okunduysa onunla, değilse önceki okunuş."""
    erisim = erisim_durumu(
        durum=200, son_url=sayfa.son_url, baslik=sayfa.baslik, metin_uzunlugu=len(sayfa.metin)
    )
    if erisim is not ErisimDurumu.ACIK:
        return onceki
    metin = f"Başlık: {sayfa.baslik}\n\n{sayfa.metin}" if sayfa.baslik else sayfa.metin
    return dataclasses.replace(onceki, erisim=erisim, baslik=sayfa.baslik, metin=metin)


def _okundu_mu(belge: KanitBelgesi) -> bool:
    return belge.erisim is ErisimDurumu.ACIK or bool(belge.ekran_goruntuleri)


async def yedekle(
    url: httpx.URL, belge: KanitBelgesi, yedek: YedekOkuyucu, uzak: UzakOkuyucu
) -> KanitBelgesi:
    if not yedek_gerekli_mi(url, belge):
        return belge
    sayfa = await yedek.ac(str(url), ekran=ekran_kurali(url), en_az_metin=EN_AZ_METIN)
    sonuc = birlestir(str(url), belge, sayfa) if sayfa is not None else belge
    if not _okundu_mu(sonuc):
        uzak_sayfa = await uzak.oku(str(url))
        if uzak_sayfa is not None:
            sonuc = uzak_birlestir(sonuc, uzak_sayfa)
    logger.info(
        "yedek okuyucu url_host=%s once=%s sonra=%s ekran=%d",
        url.host,
        belge.erisim.value,
        sonuc.erisim.value,
        len(sonuc.ekran_goruntuleri),
    )
    return sonuc
