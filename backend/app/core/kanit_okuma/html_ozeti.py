"""HTML'den başlık, açıklama, yazarlar ve ana metin (standart kütüphane; doğrusal süre).

Regex yok: büyük sayfalarda felaket geri izlemeye düşen eski başlık okuması
sunucuyu donduruyordu (bulgu 50). Ana metin için script, stil ve sayfa iskeleti
(nav, header, footer, aside) atlanır. Yazarlar `meta author`, `article:author`,
akademik sayfaların `citation_author` etiketleri (DergiPark, arXiv…) ve JSON-LD'den
okunur. Karakter kodları (`&#x2019;`) çözülür.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

EN_UZUN_METIN = 300_000
_ATLANAN = frozenset(
    {"script", "style", "noscript", "template", "svg", "nav", "header", "footer", "aside", "head"}
)
_YAZAR_ANAHTARLARI = frozenset({"author", "article:author", "citation_author", "dc.creator"})


@dataclass
class HtmlOzeti:
    baslik: str | None = None
    meta: dict[str, str] = field(default_factory=dict)
    yazarlar: list[str] = field(default_factory=list)
    metin: str = ""

    @property
    def aciklama(self) -> str | None:
        return self.meta.get("description") or self.meta.get("og:description")

    @property
    def gorunen_baslik(self) -> str | None:
        return self.baslik or self.meta.get("og:title")


class _Ayristirici(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ozet = HtmlOzeti()
        self._atlama = 0
        self._baslikta = False
        self._baslik: list[str] = []
        self._json_ld = False
        self._json_ld_icerik: list[str] = []
        self._metin: list[str] = []
        self._uzunluk = 0

    def handle_starttag(self, etiket: str, oznitelikler: list[tuple[str, str | None]]) -> None:
        degerler = {ad: deger or "" for ad, deger in oznitelikler}
        if etiket == "title" and self.ozet.baslik is None:
            self._baslikta = True
        elif etiket == "meta":
            self._meta(degerler)
        elif etiket == "script" and "ld+json" in degerler.get("type", ""):
            self._json_ld, self._json_ld_icerik = True, []
        if etiket in _ATLANAN:
            self._atlama += 1

    def handle_endtag(self, etiket: str) -> None:
        if etiket == "title" and self._baslikta:
            self._baslikta = False
            self.ozet.baslik = " ".join("".join(self._baslik).split()) or None
        elif etiket == "script" and self._json_ld:
            self._json_ld = False
            self._json_ld_yazarlari("".join(self._json_ld_icerik))
        if etiket in _ATLANAN and self._atlama:
            self._atlama -= 1

    def handle_data(self, veri: str) -> None:
        if self._baslikta:
            self._baslik.append(veri)
        elif self._json_ld:
            self._json_ld_icerik.append(veri)
        elif not self._atlama and self._uzunluk < EN_UZUN_METIN and veri.strip():
            self._metin.append(veri)
            self._uzunluk += len(veri)

    def _meta(self, degerler: dict[str, str]) -> None:
        icerik = degerler.get("content", "").strip()
        if not icerik:
            return
        for anahtar_ozniteligi in ("name", "property"):
            anahtar = degerler.get(anahtar_ozniteligi, "").strip().lower()
            if not anahtar:
                continue
            if anahtar in _YAZAR_ANAHTARLARI:
                self._yazar_ekle(icerik)
            self.ozet.meta.setdefault(anahtar, icerik)

    def _json_ld_yazarlari(self, icerik: str) -> None:
        try:
            veri: Any = json.loads(icerik)
        except ValueError:
            return
        for oge in veri if isinstance(veri, list) else [veri]:
            if not isinstance(oge, dict):
                continue
            yazar = oge.get("author") or oge.get("creator")
            for kisi in yazar if isinstance(yazar, list) else [yazar]:
                if isinstance(kisi, dict) and isinstance(kisi.get("name"), str):
                    self._yazar_ekle(kisi["name"])
                elif isinstance(kisi, str):
                    self._yazar_ekle(kisi)

    def _yazar_ekle(self, ad: str) -> None:
        temiz = " ".join(ad.split())
        if temiz and temiz not in self.ozet.yazarlar and not temiz.startswith("http"):
            self.ozet.yazarlar.append(temiz)

    def bitir(self) -> HtmlOzeti:
        self.ozet.metin = " ".join(" ".join(self._metin).split())[:EN_UZUN_METIN]
        return self.ozet


def html_ozeti(html: str) -> HtmlOzeti:
    ayristirici = _Ayristirici()
    ayristirici.feed(html)
    ayristirici.close()
    return ayristirici.bitir()
