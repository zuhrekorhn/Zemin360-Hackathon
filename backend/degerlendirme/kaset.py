"""Kaset deseni: ağ ve model yanıtlarını bir kez kaydet, sonra çevrimdışı oynat.

Karne her commit'te aynı girdilerle üretilmeli; canlı ağ (sayfalar değişir) ve
canlı model (her çağrı farklı yanıt verebilir) bunu bozar. Kayıt kipinde gerçek
çağrı yapılır ve yanıt dosyaya yazılır; oynatma kipinde yalnızca dosya okunur,
kayıtta olmayan çağrı `KasetEksik` hatasıdır (sessizce ağa çıkılmaz).

Dört kayıt:
  - `dns.json`: alan adı → IP listesi ya da çözülemedi. `guvenli_istek` isteği
    atmadan önce adresi çözüyor; oynatmada çözümleyici de kayıttan döner.
  - `ag.json` + `govdeler/`: istek anahtarı → durum, başlıklar, gövde (gzip).
    Anahtar `Host` başlığından kurulur: `guvenli_istek` bağlantıyı IP'ye açar.
  - `model.json`: iş adı + girdi özeti → model çıktısı.
  - `yedek_okuyucu.json` + `yedek/`: yedek okuyucu (Playwright servisi) yanıtları;
    HTML gzip'li, ekran görüntüleri JPEG olarak.
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
from app.core.dis_servisler.yedek_okuyucu import EkranKurali, TarayiciSayfasi, YedekOkuyucu

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
    # Sıfırdan kaydet (yalnızca yeni vaka eklenince; sayfalar zamanla değişir).
    KAYDET = "kaydet"
    # Kayıtlı olanı oynat, olmayanı canlı çek ve ekle (yeni okuyucu yeni istek atınca).
    TAMAMLA = "tamamla"


class KasetEksik(LookupError):
    """Oynatma kipinde kayıtta olmayan çağrı."""


def _ozet(metin: str) -> str:
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()


def _json_oku(yol: Path) -> dict[str, Any]:
    if not yol.exists():
        return {}
    ham = gzip.decompress(yol.read_bytes()) if yol.suffix == ".gz" else yol.read_bytes()
    return json.loads(ham.decode("utf-8"))


def _json_yaz(yol: Path, veri: dict[str, Any]) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    metin = json.dumps(veri, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if yol.suffix == ".gz":
        yol.write_bytes(gzip.compress(metin.encode("utf-8"), mtime=0))
    else:
        yol.write_text(metin, encoding="utf-8")


def _hata_sinifi(ad: str) -> type[httpx.TransportError]:
    """Kaydedilen ağ hatasının aynısı (ConnectTimeout, ReadTimeout…): okuyucular
    hatanın türüne göre durum veriyor, oynatma farklı tür üretirse sonuç değişir."""
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
        canli = self.kip is KasetKipi.KAYDET
        if canli or (self.kip is KasetKipi.TAMAMLA and host not in self._dns):
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
        if self.kip is KasetKipi.TAMAMLA:
            return _TamamlayanTransport(self)
        return httpx.MockTransport(self._oynat)

    def kayitta_mi(self, istek: httpx.Request) -> bool:
        return istek_anahtari(istek) in self._ag

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
        if self.kip is KasetKipi.OYNAT:
            return
        _json_yaz(self.klasor / "dns.json", self._dns)
        _json_yaz(self.klasor / "ag.json", self._ag)
        if self.kip is not KasetKipi.KAYDET:
            return  # tamamla kipi eski gövdeleri silmez
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


class _TamamlayanTransport(httpx.AsyncBaseTransport):
    """Kayıtlı isteği oynatır; kayıtta olmayanı gerçek ağdan çekip kasete ekler."""

    def __init__(self, kaset: AgKaseti) -> None:
        self._kaset = kaset
        self._kaydeden = _KaydedenTransport(kaset)

    async def handle_async_request(self, istek: httpx.Request) -> httpx.Response:
        if self._kaset.kayitta_mi(istek):
            return self._kaset._oynat(istek)
        return await self._kaydeden.handle_async_request(istek)

    async def aclose(self) -> None:
        await self._kaydeden.aclose()


class ModelKaseti:
    """Model (ve embedding) çağrıları: aynı iş + aynı girdi → kayıtlı çıktı.

    Kaydet ve tamamla kipleri aynı davranır: kayıtlı girdi yeniden çağrılmaz,
    yalnızca eksik olan çağrılır; dosyaya o çalıştırmada kullanılanlar yazılır.
    """

    def __init__(
        self, kip: KasetKipi, klasor: Path = KASET_KLASORU, dosya: str = "model.json"
    ) -> None:
        self.kip = kip
        self.klasor = klasor
        self.dosya = dosya
        self._kayit: dict[str, Any] = _json_oku(klasor / dosya)
        # Eski kayıtlar önbellektir (yeniden çağrılmaz), ama dosyaya yalnızca bu
        # çalıştırmada kullanılanlar yazılır.
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
        if self.kip is not KasetKipi.OYNAT:
            if anahtar not in self._kayit:
                self._kayit[anahtar] = await gercek()
            self._kullanilan.add(anahtar)
            return self._kayit[anahtar]
        if anahtar not in self._kayit:
            raise KasetEksik(f"model kaydı yok: {anahtar}")
        return self._kayit[anahtar]

    def kaydet(self) -> None:
        if self.kip is not KasetKipi.OYNAT:
            _json_yaz(
                self.klasor / self.dosya,
                {a: c for a, c in self._kayit.items() if a in self._kullanilan},
            )


class YedekOkuyucuKaseti:
    """Yedek okuyucunun yanıtları. Kayıt ve tamamlama kipinde gerçek servis çağrılır
    (yerelde `python -m yedek_okuyucu` çalışıyor olmalı); servis ayakta değilse
    sessizce "okunamadı" kaydedilmez, hata verilir."""

    kip = "kaset"

    def __init__(
        self, kip: KasetKipi, gercek: YedekOkuyucu | None = None, klasor: Path = KASET_KLASORU
    ) -> None:
        self.kaset_kipi = kip
        self.klasor = klasor
        self._gercek = gercek
        self._servis_denetlendi = False
        kayitta = kip is KasetKipi.KAYDET
        self._kayit: dict[str, Any] = {} if kayitta else _json_oku(klasor / "yedek_okuyucu.json")

    @property
    def _yedek_klasoru(self) -> Path:
        return self.klasor / "yedek"

    async def ac(self, url: str, *, ekran: EkranKurali, en_az_metin: int) -> TarayiciSayfasi | None:
        anahtar = f"{url} {ekran.value} {en_az_metin}"
        canli = self.kaset_kipi is KasetKipi.KAYDET or (
            self.kaset_kipi is KasetKipi.TAMAMLA and anahtar not in self._kayit
        )
        if canli:
            sayfa = await self._canli(url, ekran, en_az_metin)
            self._kayit[anahtar] = self._yaz(anahtar, sayfa)
            return sayfa
        if anahtar not in self._kayit:
            raise KasetEksik(f"yedek okuyucu kaydı yok: {anahtar}")
        return self._oku(self._kayit[anahtar])

    async def _canli(
        self, url: str, ekran: EkranKurali, en_az_metin: int
    ) -> TarayiciSayfasi | None:
        if self._gercek is None:
            from app.core.dis_servisler import kurulum

            self._gercek = kurulum.yedek_okuyucu()
        if not self._servis_denetlendi:
            await self._servisi_denetle()
        return await self._gercek.ac(url, ekran=ekran, en_az_metin=en_az_metin)

    async def _servisi_denetle(self) -> None:
        from app.core.config import get_settings

        adres = get_settings().yedek_okuyucu_adresi.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=5) as istemci:
                (await istemci.get(f"{adres}/saglik")).raise_for_status()
        except httpx.HTTPError as hata:
            raise RuntimeError(
                f"Yedek okuyucu servisi çalışmıyor ({adres}); kayıttan önce "
                "`python -m yedek_okuyucu` ile başlatın."
            ) from hata
        self._servis_denetlendi = True

    def _yaz(self, anahtar: str, sayfa: TarayiciSayfasi | None) -> dict[str, Any]:
        if sayfa is None:
            return {"yok": True}
        ozet = _ozet(anahtar)[:20]
        self._yedek_klasoru.mkdir(parents=True, exist_ok=True)
        (self._yedek_klasoru / f"{ozet}.html.gz").write_bytes(
            gzip.compress(sayfa.html.encode("utf-8"), mtime=0)
        )
        ekranlar = []
        for i, goruntu in enumerate(sayfa.ekran_goruntuleri):
            dosya = f"{ozet}-{i}.jpg"
            (self._yedek_klasoru / dosya).write_bytes(goruntu)
            ekranlar.append(dosya)
        return {
            "durum": sayfa.durum,
            "son_url": sayfa.son_url,
            "html": f"{ozet}.html.gz",
            "ekranlar": ekranlar,
        }

    def _oku(self, kayit: dict[str, Any]) -> TarayiciSayfasi | None:
        if kayit.get("yok"):
            return None
        html = gzip.decompress((self._yedek_klasoru / kayit["html"]).read_bytes()).decode("utf-8")
        return TarayiciSayfasi(
            durum=kayit["durum"],
            son_url=kayit["son_url"],
            html=html,
            ekran_goruntuleri=tuple(
                (self._yedek_klasoru / d).read_bytes() for d in kayit.get("ekranlar", [])
            ),
        )

    def kaydet(self) -> None:
        if self.kaset_kipi is KasetKipi.OYNAT:
            return
        _json_yaz(self.klasor / "yedek_okuyucu.json", self._kayit)
        if self.kaset_kipi is not KasetKipi.KAYDET or not self._yedek_klasoru.exists():
            return
        kullanilan = {k["html"] for k in self._kayit.values() if k.get("html")} | {
            d for k in self._kayit.values() for d in k.get("ekranlar", [])
        }
        for dosya in self._yedek_klasoru.iterdir():
            if dosya.name not in kullanilan:
                dosya.unlink()
