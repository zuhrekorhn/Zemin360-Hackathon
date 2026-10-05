"""Sayfayı gerçek bir tarayıcıda açar: işlenmiş HTML ve gerekirse ekran görüntüsü (plan § 5.5).

JavaScript ile çizilen sayfa (Kaggle, GrabCAD) ve tarayıcı olmayan istemciyi
reddeden site (Behance, Dribbble) burada okunur. Tarayıcının bütün ağı süzgeçli
vekilden geçer (`vekil.py`). Ekran görüntüsü: 1280 px genişlik, sayfanın
yukarıdan aşağı en çok 3 parçası, JPEG.

Ne zaman ekran görüntüsü alınacağına backend karar verir (`ekran` kuralı ve
`en_az_metin` eşiği istekle gelir); burada yalnızca uygulanır.
"""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass, field
from enum import StrEnum

from playwright.async_api import Browser, Playwright, async_playwright
from playwright.async_api import Error as PlaywrightHatasi
from playwright.async_api import TimeoutError as PlaywrightZamanAsimi

from app.core.guvenli_istek import AdresBulunamadi, GuvensizAdres, hedefi_dogrula

logger = logging.getLogger("zemin360.yedek_okuyucu")

EKRAN_GENISLIGI = 1280
PARCA_YUKSEKLIGI = 1600
EN_COK_PARCA = 3
JPEG_KALITESI = 70
GEZINME_ZAMAN_ASIMI_MS = 20_000
# Sayfa açıldıktan sonra ağın durulmasını en çok bu kadar bekler (sonsuz yoklayan
# sayfa yüzünden takılmasın).
SAKINLESME_MS = 5_000
EN_BUYUK_HTML = 2_000_000
# Okurken sayfa yeniden gezinirse (doğrulama ara sayfası) okuma bu kadar kez yenilenir.
YENIDEN_DENEME = 2
TARAYICI_DILI = "tr-TR"


class EkranKurali(StrEnum):
    HER_ZAMAN = "her_zaman"
    # Görünür metin `en_az_metin`'den kısaysa (JavaScript ile çizilen, görsel ağırlıklı sayfa)
    METIN_AZSA = "metin_azsa"
    HAYIR = "hayir"


class AcilisHatasi(StrEnum):
    GUVENSIZ = "guvensiz"
    BULUNAMADI = "bulunamadi"
    ZAMAN_ASIMI = "zaman_asimi"
    # Ağ hatası, indirme (sayfa değil dosya), tarayıcı hatası
    ACILAMADI = "acilamadi"


@dataclass
class Acilis:
    durum: int | None = None
    son_url: str = ""
    html: str = ""
    ekran_goruntuleri: list[bytes] = field(default_factory=list)
    hata: AcilisHatasi | None = None


class SayfaAcici:
    """Tek tarayıcı süreci; her istek kendi bağlamında (çerez ve depolama paylaşılmaz)."""

    def __init__(self, vekil_portu: int, eszamanli: int = 2) -> None:
        self._vekil_portu = vekil_portu
        self._sinir = asyncio.Semaphore(eszamanli)
        self._pw: Playwright | None = None
        self._tarayici: Browser | None = None
        self._kullanici_araci = ""

    async def baslat(self) -> None:
        self._pw = await async_playwright().start()
        self._tarayici = await self._pw.chromium.launch(
            # Tam Chromium'un yeni başsız kipi (ayrı "headless shell" değil): siteler
            # onu sıradan bir tarayıcı gibi görür.
            channel="chromium",
            # "<-loopback>": Chromium yerel adresleri varsayılan olarak vekilsiz açar;
            # bu kural onu da vekile zorlar (vekil reddeder).
            proxy={"server": f"http://127.0.0.1:{self._vekil_portu}", "bypass": "<-loopback>"},
            # WebRTC vekili atlayıp UDP açmasın.
            args=[
                "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        # Kullanıcı aracında "HeadlessChrome" yazmasın (bazı siteler yalnızca buna bakıp
        # 403 veriyor).
        self._kullanici_araci = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{self._tarayici.version} Safari/537.36"
        )

    async def durdur(self) -> None:
        if self._tarayici is not None:
            await self._tarayici.close()
        if self._pw is not None:
            await self._pw.stop()

    async def ac(self, url: str, ekran: EkranKurali, en_az_metin: int) -> Acilis:
        try:
            await hedefi_dogrula(url)
        except AdresBulunamadi:
            return Acilis(hata=AcilisHatasi.BULUNAMADI)
        except GuvensizAdres:
            return Acilis(hata=AcilisHatasi.GUVENSIZ)
        assert self._tarayici is not None, "baslat() çağrılmadı"
        async with self._sinir:
            baglam = await self._tarayici.new_context(
                viewport={"width": EKRAN_GENISLIGI, "height": PARCA_YUKSEKLIGI},
                locale=TARAYICI_DILI,
                user_agent=self._kullanici_araci,
                service_workers="block",
                accept_downloads=False,
            )
            try:
                return await self._oku(await baglam.new_page(), url, ekran, en_az_metin)
            finally:
                await baglam.close()

    async def _oku(self, sayfa, url: str, ekran: EkranKurali, en_az_metin: int) -> Acilis:
        # Durum, ana çerçevenin SON belgesinden: bot doğrulaması yapan site önce 202 /
        # 403'lük bir ara sayfa verir, tarayıcı onu geçince asıl sayfaya gider.
        son_durum: list[int] = []

        def belge_geldi(yanit) -> None:
            if yanit.request.is_navigation_request() and yanit.frame == sayfa.main_frame:
                son_durum.append(yanit.status)

        sayfa.on("response", belge_geldi)
        try:
            await sayfa.goto(url, wait_until="domcontentloaded", timeout=GEZINME_ZAMAN_ASIMI_MS)
        except PlaywrightZamanAsimi:
            return Acilis(hata=AcilisHatasi.ZAMAN_ASIMI)
        except PlaywrightHatasi as hata:
            logger.info("sayfa acilamadi url=%s hata=%s", url, _ilk_satir(hata))
            return Acilis(hata=AcilisHatasi.ACILAMADI)
        for deneme in range(YENIDEN_DENEME + 1):
            try:
                metin, html, goruntuler = await _icerigi_al(sayfa, ekran, en_az_metin)
                break
            except PlaywrightHatasi as hata:
                # Okurken sayfa yeniden gezindi (doğrulama sayfası geçildi): yeni belge beklenir.
                if deneme == YENIDEN_DENEME:
                    logger.info("sayfa okunamadi url=%s hata=%s", url, _ilk_satir(hata))
                    return Acilis(hata=AcilisHatasi.ACILAMADI)
                await _bekle(sayfa, "load", GEZINME_ZAMAN_ASIMI_MS)
        return Acilis(
            durum=son_durum[-1] if son_durum else None,
            son_url=sayfa.url,
            html=html[:EN_BUYUK_HTML],
            ekran_goruntuleri=goruntuler,
        )


def _ilk_satir(hata: Exception) -> str:
    return (str(hata).splitlines() or [""])[0][:200]


async def _bekle(sayfa, durum: str, zaman_asimi_ms: int) -> None:
    try:
        await sayfa.wait_for_load_state(durum, timeout=zaman_asimi_ms)
    except PlaywrightZamanAsimi:
        pass  # sürekli yoklayan sayfa: olduğu kadarıyla okunur


async def _icerigi_al(sayfa, ekran: EkranKurali, en_az_metin: int) -> tuple[str, str, list[bytes]]:
    await _bekle(sayfa, "networkidle", SAKINLESME_MS)
    await _tembel_yuklemeyi_tetikle(sayfa)
    metin = await sayfa.evaluate("document.body ? document.body.innerText : ''")
    goruntuler: list[bytes] = []
    if ekran is EkranKurali.HER_ZAMAN or (
        ekran is EkranKurali.METIN_AZSA and len(metin.strip()) < en_az_metin
    ):
        goruntuler = await _ekran_goruntuleri(sayfa)
    return metin, await sayfa.content(), goruntuler


async def _tembel_yuklemeyi_tetikle(sayfa) -> None:
    """Görüntülenecek bölümü aşağı doğru kaydırır: tembel yüklenen görseller gelsin."""
    for i in range(1, EN_COK_PARCA + 1):
        await sayfa.evaluate(f"window.scrollTo(0, {i * PARCA_YUKSEKLIGI})")
        await sayfa.wait_for_timeout(300)
    await sayfa.evaluate("window.scrollTo(0, 0)")
    await _bekle(sayfa, "networkidle", 2_000)


async def _ekran_goruntuleri(sayfa) -> list[bytes]:
    yukseklik = await sayfa.evaluate(
        "Math.max(document.documentElement.scrollHeight,"
        " document.body ? document.body.scrollHeight : 0)"
    )
    parca_sayisi = max(1, min(EN_COK_PARCA, math.ceil((yukseklik or 1) / PARCA_YUKSEKLIGI)))
    goruntuler = []
    for i in range(parca_sayisi):
        ust = i * PARCA_YUKSEKLIGI
        boy = max(1, min(PARCA_YUKSEKLIGI, (yukseklik or PARCA_YUKSEKLIGI) - ust))
        goruntuler.append(
            await sayfa.screenshot(
                full_page=True,
                clip={"x": 0, "y": ust, "width": EKRAN_GENISLIGI, "height": boy},
                type="jpeg",
                quality=JPEG_KALITESI,
            )
        )
    return goruntuler
