"""Kanıt linkinin erişilebilirliği ve `<head>` özeti.

Geçici modül: plan § 5'teki okuyucu zinciri (`app/core/kanit_okuma/`) gelince
yerini ona bırakır (docs/plans/dogrulama-iyilestirme.md, adım 5).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

from app.agents.dogrulama.kurallar import OkunanKanit
from app.core.guvenli_istek import GuvensizAdres, guvenli_get
from app.core.kanit_okuma.belge import ErisimDurumu, KaynakSeviyesi

logger = logging.getLogger("zemin360.dogrulama")

LINK_YOK = "kanıt linki yok"
GUVENSIZ_ADRES = "adres herkese açık bir web sayfası değil"
OZET_OKUNAMADI = "(başlık/açıklama okunamadı)"

LINK_TIMEOUT_SANIYE = 8
# Sayfanın tamamı çekilmiyor: <head> bitene kadar okunuyor. Sabit bir ilk
# parça yetmiyordu — GitHub gibi siteler <title>'ı 20 KB'ın ötesine atıyor.
# Üst sınır, <head>'i hiç kapatmayan sayfalarda okumayı durdurmak için.
INDIRILEN_BAYT = 300_000


@dataclass(frozen=True)
class LinkKontrolu:
    erisilebilir: bool
    durum_kodu: int | None
    ozet: str
    aciklama: str

    @property
    def erisim(self) -> ErisimDurumu | None:
        """Plan § 5.2'deki erişim durumu; link yoksa None.

        Geçici eşleme: okuyucu zinciri (adım 5) durumu doğrudan üretecek. Alan adı
        çözülemeyen adres bugün `GUVENSIZ`'e düşüyor (bulgu 6, adım 5'te ayrılır).
        """
        if self.aciklama == LINK_YOK:
            return None
        if self.erisilebilir:
            return ErisimDurumu.ICERIK_YOK if self.ozet == OZET_OKUNAMADI else ErisimDurumu.ACIK
        if self.durum_kodu in (404, 410):
            return ErisimDurumu.BULUNAMADI
        if self.durum_kodu == 401:
            return ErisimDurumu.GIRIS_GEREKLI
        if self.durum_kodu is not None:
            return ErisimDurumu.HATA if self.durum_kodu >= 500 else ErisimDurumu.ENGELLENDI
        if self.aciklama == GUVENSIZ_ADRES:
            return ErisimDurumu.GUVENSIZ
        return ErisimDurumu.HATA


def okunan_kanit(kontrol: LinkKontrolu, url: str | None) -> OkunanKanit | None:
    """Link kontrolünü çekirdeğin girdisine çevirir. Bağlı hesap (B) adım 8'de;
    bugün okunan herkese açık link seviye C'dir."""
    erisim = kontrol.erisim
    if erisim is None:
        return None
    metin = kontrol.ozet if erisim is ErisimDurumu.ACIK else ""
    return OkunanKanit(erisim=erisim, seviye=KaynakSeviyesi.KAMUYA_ACIK, metin=metin, url=url)


def linki_normalize_et(kanit_linki: str) -> str:
    """Şeması olmayan linke https:// ekler.

    Kullanıcılar sohbette linki çoğu zaman "github.com/..." diye yazıyor;
    şemasız adres httpx'e verilemez ve kanıt haksız yere "açılmıyor" sayılır.
    """
    link = kanit_linki.strip()
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", link):
        return link
    return f"https://{link.lstrip('/')}"


class _HeadBitti(Exception):
    """`</head>` görüldü: başlık ve meta etiketleri orada biter, gövde okunmaz."""


class _BaslikAyristirici(HTMLParser):
    """`<head>`'den `<title>` ve meta etiketlerini okur.

    Standart kütüphanenin HTML ayrıştırıcısı: süre sayfa boyuyla doğrusal
    artar. Eski regex'li okuma (`(.*?)` + `re.S`) büyük `<head>`'de felaket geri
    izlemeye düşüyor, 300 KB'lık bir sayfada saatler sürüyordu. Python'ın regex
    motoru eşleşme boyunca GIL'i bırakmadığı için bu, bütün sunucuyu donduruyordu.
    Öznitelik değerlerindeki karakter kodları (`&#x2019;`) da burada çözülür.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.baslik: str | None = None
        self.meta: dict[str, str] = {}
        self._baslik_parcalari: list[str] | None = None

    def handle_starttag(self, etiket: str, oznitelikler: list[tuple[str, str | None]]) -> None:
        if etiket == "title" and self.baslik is None:
            self._baslik_parcalari = []
        elif etiket == "meta":
            degerler = {ad: deger or "" for ad, deger in oznitelikler}
            icerik = degerler.get("content", "")
            if not icerik.strip():
                return
            # Open Graph `property=`, diğerleri `name=` kullanıyor; ilk görülen kazanır.
            for anahtar_ozniteligi in ("name", "property"):
                anahtar = degerler.get(anahtar_ozniteligi, "").strip().lower()
                if anahtar:
                    self.meta.setdefault(anahtar, icerik)

    def handle_data(self, veri: str) -> None:
        if self._baslik_parcalari is not None:
            self._baslik_parcalari.append(veri)

    def handle_endtag(self, etiket: str) -> None:
        if etiket == "title" and self._baslik_parcalari is not None:
            self.baslik = "".join(self._baslik_parcalari)
            self._baslik_parcalari = None
        elif etiket == "head":
            raise _HeadBitti


def link_ozetini_cikar(html: str) -> str:
    """Sayfadan başlık ve açıklamayı alır (tam içerik çekilmiyor).

    Başlık için <title>, yoksa og:title; açıklama için meta description,
    yoksa og:description.
    """
    ayristirici = _BaslikAyristirici()
    try:
        ayristirici.feed(html)
        ayristirici.close()
    except _HeadBitti:
        pass

    baslik = (
        ayristirici.baslik if ayristirici.baslik is not None else ayristirici.meta.get("og:title")
    )
    aciklama = ayristirici.meta.get("description") or ayristirici.meta.get("og:description")

    parcalar = [" ".join(p.split()) for p in (baslik, aciklama) if p and p.strip()]
    ozet = " — ".join(parcalar)
    return ozet[:400] or OZET_OKUNAMADI


# --- Kanıt kontrolü --------------------------------------------------------


async def linki_kontrol_et(
    kanit_linki: str | None, *, transport: httpx.AsyncBaseTransport | None = None
) -> LinkKontrolu:
    """Link gerçekten açılıyor mu? İçerik analizi yok, erişilebilirlik var.

    İstek `app/core/guvenli_istek.py` üzerinden: iç ağa, desteklenmeyen şemaya
    ya da porta giden adres (yönlendirme adımları dahil) hiç istenmez ve link
    "açılmıyor" sayılır (SSRF engeli). `transport` yalnızca testler için.
    """
    if not kanit_linki:
        return LinkKontrolu(False, None, "(kanıt linki verilmedi)", LINK_YOK)

    adres = linki_normalize_et(kanit_linki)
    try:
        async with guvenli_get(
            adres, zaman_asimi=LINK_TIMEOUT_SANIYE, transport=transport
        ) as yanit:
            if not yanit.is_success:
                return LinkKontrolu(
                    False, yanit.status_code, "(sayfa açılmadı)", f"HTTP {yanit.status_code}"
                )
            govde = await _basligi_oku(yanit)
    except GuvensizAdres as hata:
        logger.info("Kanıt linki güvenli değil, istenmedi: %s (%s)", adres, hata)
        return LinkKontrolu(False, None, "(sayfa açılmadı)", GUVENSIZ_ADRES)
    except httpx.HTTPError as hata:
        return LinkKontrolu(False, None, "(sayfa açılmadı)", f"erişilemedi: {type(hata).__name__}")

    return LinkKontrolu(True, yanit.status_code, link_ozetini_cikar(govde), "açılıyor")


async def _basligi_oku(yanit: httpx.Response) -> str:
    """Sayfayı `</head>` görülene ya da üst sınıra kadar okur.

    İndirmeyi erken kesiyoruz: ihtiyacımız olan her şey <head> içinde ve
    büyük sayfaların gövdesini çekmenin anlamı yok.
    """
    parcalar: list[str] = []
    uzunluk = 0
    async for parca in yanit.aiter_text():
        parcalar.append(parca)
        uzunluk += len(parca)
        if "</head>" in parca.lower() or uzunluk >= INDIRILEN_BAYT:
            break
    return "".join(parcalar)
