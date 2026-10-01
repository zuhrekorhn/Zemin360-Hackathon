"""Kaset deseni: ağ ve model yanıtlarını bir kez kaydet, sonra çevrimdışı oynat.

Karne her commit'te aynı girdilerle üretilmeli; canlı ağ (sayfalar değişir) ve
canlı model (her çağrı farklı yanıt verebilir) bunu bozar. Kayıt kipinde gerçek
çağrı yapılır ve yanıt dosyaya yazılır; oynatma kipinde yalnızca dosya okunur,
kayıtta olmayan çağrı `KasetEksik` hatasıdır (sessizce ağa çıkılmaz).

Üç kayıt:
  - `dns.json`: alan adı → IP listesi ya da çözülemedi. `guvenli_istek` isteği
    atmadan önce adresi çözüyor; oynatmada çözümleyici de kayıttan döner.
  - `ag.json` + `govdeler/`: istek anahtarı → durum, başlıklar, gövde (gzip).
    Anahtar `Host` başlığından kurulur: `guvenli_istek` bağlantıyı IP'ye açar.
  - `model.json`: iş adı + girdi özeti → model çıktısı.
"""

from __future__ import annotations

import gzip
import hashlib
import ipaddress
import json
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from typing import Any

import httpx

from app.core import guvenli_istek

KASET_KLASORU = Path(__file__).resolve().parent.parent / "tests" / "degerlendirme_seti" / "kaset"

# Kayıtta saklanan en büyük gövde. Okuyucular 2 MB'a kadar okuyacak (plan § 5.3).
EN_BUYUK_GOVDE = 3_000_000
SAKLANAN_BASLIKLAR = ("content-type", "location", "content-encoding")
# Gövde gerçek ağdaki gibi parça parça akar. Tek parça vermek okuyucunun
# davranışını değiştirir: "ilk N baytı oku, kes" mantığı tek parçada bütün
# sayfayı görür (bugünkü başlık ayrıştırmasının takılması bu yüzden kayboluyordu).
AKIS_PARCASI = 65_536


class _ParcaliAkis(httpx.AsyncByteStream):
    def __init__(self, govde: bytes) -> None:
        self._govde = govde

    async def __aiter__(self):
        for i in range(0, len(self._govde), AKIS_PARCASI):
            yield self._govde[i : i + AKIS_PARCASI]


def _parcali_yanit(
    durum: int, basliklar: Any, govde: bytes, istek: httpx.Request
) -> httpx.Response:
    return httpx.Response(durum, headers=basliklar, stream=_ParcaliAkis(govde), request=istek)


class KasetKipi(StrEnum):
    OYNAT = "oynat"
    KAYDET = "kaydet"


class KasetEksik(LookupError):
    """Oynatma kipinde kayıtta olmayan çağrı."""


def _ozet(metin: str) -> str:
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()


def _json_oku(yol: Path) -> dict[str, Any]:
    return json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else {}


def _json_yaz(yol: Path, veri: dict[str, Any]) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(
        json.dumps(veri, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )


def _hata_sinifi(ad: str) -> type[httpx.TransportError]:
    """Kaydedilen ağ hatasının aynısı (ConnectTimeout, ReadTimeout…): okuyucular
    hatanın türünü metne yazıyor, oynatma farklı tür üretirse sonuç değişir."""
    sinif = getattr(httpx, ad, None)
    if isinstance(sinif, type) and issubclass(sinif, httpx.TransportError):
        return sinif
    return httpx.ConnectError


def istek_anahtari(istek: httpx.Request) -> str:
    """IP'ye sabitlenmiş istekte de özgün adresi verir (`Host` başlığından)."""
    host = istek.headers.get("host") or istek.url.netloc.decode("ascii")
    yol = istek.url.raw_path.decode("ascii")
    return f"{istek.method} {istek.url.scheme}://{host}{yol}"


class AgKaseti:
    """DNS ve HTTP yanıtları. Bir kip için kurulur; `kaydet()` dosyaları yazar."""

    def __init__(self, kip: KasetKipi, klasor: Path = KASET_KLASORU) -> None:
        self.kip = kip
        self.klasor = klasor
        # Kayıt kipi sıfırdan başlar: kaset, yalnızca bu çalıştırmanın yaptığı
        # isteklerden oluşur (silinen vakanın kaydı kalmaz).
        kayitta = kip is KasetKipi.KAYDET
        self._dns: dict[str, list[str] | None] = {} if kayitta else _json_oku(klasor / "dns.json")
        self._ag: dict[str, dict[str, Any]] = {} if kayitta else _json_oku(klasor / "ag.json")

    # --- DNS ---------------------------------------------------------------

    async def cozumle(self, host: str, port: int) -> list[guvenli_istek.IpAdresi]:
        if self.kip is KasetKipi.KAYDET:
            try:
                ipler = await guvenli_istek._sistem_cozumleyicisi(host, port)
            except (OSError, UnicodeError):
                self._dns[host] = None
                raise
            self._dns[host] = [str(ip) for ip in ipler]
            return ipler

        if host not in self._dns:
            raise KasetEksik(f"DNS kaydı yok: {host}")
        kayit = self._dns[host]
        if kayit is None:
            raise OSError(f"kayıtta çözülemedi: {host}")
        return [ipaddress.ip_address(ip) for ip in kayit]

    @contextmanager
    def dns_baglami(self) -> Iterator[None]:
        """`guvenli_istek.cozumleyici`'yi bu kasetle değiştirir, çıkışta geri koyar."""
        onceki = guvenli_istek.cozumleyici
        guvenli_istek.cozumleyici = self.cozumle
        try:
            yield
        finally:
            guvenli_istek.cozumleyici = onceki

    # --- HTTP --------------------------------------------------------------

    def transport(self) -> httpx.AsyncBaseTransport:
        """Kipine göre oynatan ya da gerçek ağa çıkıp kaydeden transport."""
        if self.kip is KasetKipi.KAYDET:
            return _KaydedenTransport(self)
        return httpx.MockTransport(self._oynat)

    def _oynat(self, istek: httpx.Request) -> httpx.Response:
        anahtar = istek_anahtari(istek)
        kayit = self._ag.get(anahtar)
        if kayit is None:
            raise KasetEksik(f"ağ kaydı yok: {anahtar}")
        if "hata" in kayit:
            raise _hata_sinifi(kayit["hata"])(kayit["hata"], request=istek)
        govde = b""
        if kayit.get("govde"):
            govde = gzip.decompress((self.klasor / "govdeler" / kayit["govde"]).read_bytes())
        return _parcali_yanit(kayit["durum"], kayit.get("basliklar", {}), govde, istek)

    def _kaydet_yanit(self, anahtar: str, yanit: httpx.Response, govde: bytes) -> None:
        dosya = None
        if govde:
            dosya = f"{_ozet(anahtar)[:20]}.gz"
            yol = self.klasor / "govdeler" / dosya
            yol.parent.mkdir(parents=True, exist_ok=True)
            yol.write_bytes(gzip.compress(govde[:EN_BUYUK_GOVDE], mtime=0))
        self._ag[anahtar] = {
            "durum": yanit.status_code,
            "basliklar": {
                ad: yanit.headers[ad]
                for ad in SAKLANAN_BASLIKLAR
                if ad in yanit.headers and ad != "content-encoding"
            },
            "govde": dosya,
        }

    def _kaydet_hata(self, anahtar: str, hata: Exception) -> None:
        self._ag[anahtar] = {"hata": type(hata).__name__}

    def kaydet(self) -> None:
        if self.kip is not KasetKipi.KAYDET:
            return
        _json_yaz(self.klasor / "dns.json", self._dns)
        _json_yaz(self.klasor / "ag.json", self._ag)
        kullanilan = {k["govde"] for k in self._ag.values() if k.get("govde")}
        for dosya in (self.klasor / "govdeler").glob("*.gz"):
            if dosya.name not in kullanilan:
                dosya.unlink()

    def kayitli_mi(self, url: str) -> bool:
        """Bu link için en az bir istek kaydı var mı? (set bütünlüğü testi)"""
        host = httpx.URL(url if "://" in url else f"https://{url}").host
        return host in self._dns and (
            self._dns[host] is None or any(f"://{host}" in a for a in self._ag)
        )


class _KaydedenTransport(httpx.AsyncBaseTransport):
    """Gerçek ağa çıkar, yanıtı tamamen okuyup kasete yazar, kopyasını döner."""

    def __init__(self, kaset: AgKaseti) -> None:
        self._kaset = kaset
        self._ic = httpx.AsyncHTTPTransport()

    async def handle_async_request(self, istek: httpx.Request) -> httpx.Response:
        anahtar = istek_anahtari(istek)
        try:
            yanit = await self._ic.handle_async_request(istek)
            govde = await yanit.aread()
        except httpx.HTTPError as hata:
            self._kaset._kaydet_hata(anahtar, hata)
            raise
        self._kaset._kaydet_yanit(anahtar, yanit, govde)
        basliklar = [
            (ad, deger)
            for ad, deger in yanit.headers.items()
            if ad.lower() not in ("content-encoding", "content-length")
        ]
        return _parcali_yanit(yanit.status_code, basliklar, govde, istek)

    async def aclose(self) -> None:
        await self._ic.aclose()


class ModelKaseti:
    """Model çağrıları: aynı iş + aynı girdi → kayıtlı çıktı."""

    def __init__(self, kip: KasetKipi, klasor: Path = KASET_KLASORU) -> None:
        self.kip = kip
        self.klasor = klasor
        self._kayit: dict[str, Any] = _json_oku(klasor / "model.json")
        # Kayıt kipinde eski kayıtlar önbellektir (yeniden çağrılmaz), ama
        # dosyaya yalnızca bu çalıştırmada kullanılanlar yazılır.
        self._kullanilan: set[str] = set()

    @staticmethod
    def anahtar(is_adi: str, girdi: dict[str, Any]) -> str:
        return f"{is_adi}:{_ozet(json.dumps(girdi, ensure_ascii=False, sort_keys=True))[:32]}"

    async def cagir(
        self,
        is_adi: str,
        girdi: dict[str, Any],
        gercek: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        anahtar = self.anahtar(is_adi, girdi)
        if self.kip is KasetKipi.KAYDET:
            if anahtar not in self._kayit:
                self._kayit[anahtar] = await gercek()
            self._kullanilan.add(anahtar)
            return self._kayit[anahtar]
        if anahtar not in self._kayit:
            raise KasetEksik(f"model kaydı yok: {anahtar}")
        return self._kayit[anahtar]

    def kaydet(self) -> None:
        if self.kip is KasetKipi.KAYDET:
            _json_yaz(
                self.klasor / "model.json",
                {a: c for a, c in self._kayit.items() if a in self._kullanilan},
            )
