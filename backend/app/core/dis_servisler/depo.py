"""Yüklenen kanıt dosyalarının deposu: arayüz, R2, yerel disk ve kapalı kip (plan § 4.4).

Servisler yalnızca `Depo`'ya bağlıdır; hangi sınıfın kullanılacağına
`kurulum.py` karar verir. Anahtar rastgeledir, dosya adı kullanıcıdan alınmaz.
Dosya yalnızca kısa ömürlü imzalı adresle ve indirme olarak sunulur
(`Content-Disposition: attachment`): tarayıcıda sayfa olarak açılmaz.

  - R2 (yayın): S3 uyumlu, özel kova; imzalı adres R2'nin alan adında.
  - Yerel (geliştirme): dosya diskte; imzalı adres backend'in `/dosya/{token}`
    ucuna gider (token JWT, `app/api/dosya.py`).
  - Kapalı: yükleme 503 ile reddedilir, mevcut parçalar değerlendirilmeye devam eder.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import re
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

import jwt

from app.core.dis_servisler.sarmalayicilar import gozlemli, zaman_asimli

IMZALI_ADRES_SURESI_SN = 300
_TOKEN_AMACI = "dosya"
_ANAHTAR = re.compile(r"^[a-z0-9][a-z0-9/_-]{7,199}$")


class DepoKapali(RuntimeError):
    """Depo kapalı ya da yapılandırılmamış (uçta 503)."""


class Depo(Protocol):
    # "r2" | "yerel" | "kapali": sağlık ucu ve log'lar için.
    kip: str

    async def koy(self, anahtar: str, veri: bytes, icerik_turu: str) -> None: ...

    async def al(self, anahtar: str) -> bytes: ...

    async def imzali_adres(self, anahtar: str, *, dosya_adi: str, icerik_turu: str) -> str: ...

    async def sil(self, anahtar: str) -> None: ...


def indirme_basligi(dosya_adi: str) -> str:
    """Her kipte aynı başlık: indirme olarak, ASCII dışı ad RFC 5987 ile."""
    ascii_ad = dosya_adi.encode("ascii", "ignore").decode() or "kanit"
    ascii_ad = ascii_ad.replace('"', "")
    return f"attachment; filename=\"{ascii_ad}\"; filename*=UTF-8''{quote(dosya_adi)}"


def _anahtar_gecerli(anahtar: str) -> str:
    # Yerel depoda anahtar dosya yoludur: ".." ya da mutlak yol olamaz.
    if not _ANAHTAR.match(anahtar) or ".." in anahtar:
        raise ValueError("geçersiz depo anahtarı")
    return anahtar


class YerelDepo:
    """Geliştirme: dosyalar diskte, imzalı adres backend'in indirme ucunda."""

    kip = "yerel"

    def __init__(self, klasor: Path, imza_anahtari: str, api_adresi: str) -> None:
        self._klasor = klasor
        self._imza = imza_anahtari
        self._api = api_adresi.rstrip("/")

    def yol(self, anahtar: str) -> Path:
        return self._klasor / _anahtar_gecerli(anahtar)

    async def koy(self, anahtar: str, veri: bytes, icerik_turu: str) -> None:
        yol = self.yol(anahtar)
        yol.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(yol.write_bytes, veri)

    async def al(self, anahtar: str) -> bytes:
        return await asyncio.to_thread(self.yol(anahtar).read_bytes)

    async def imzali_adres(self, anahtar: str, *, dosya_adi: str, icerik_turu: str) -> str:
        token = jwt.encode(
            {
                "amac": _TOKEN_AMACI,
                "anahtar": anahtar,
                "ad": dosya_adi,
                "tur": icerik_turu,
                "exp": dt.datetime.now(dt.UTC) + dt.timedelta(seconds=IMZALI_ADRES_SURESI_SN),
            },
            self._imza,
            algorithm="HS256",
        )
        return f"{self._api}/dosya/{token}"

    def token_coz(self, token: str) -> tuple[str, str, str]:
        """İndirme ucu için: (anahtar, dosya adı, içerik türü). Süresi geçmişse hata."""
        veri = jwt.decode(token, self._imza, algorithms=["HS256"])
        if veri.get("amac") != _TOKEN_AMACI:
            raise jwt.InvalidTokenError("amaç uyuşmuyor")
        return _anahtar_gecerli(veri["anahtar"]), veri["ad"], veri["tur"]

    async def sil(self, anahtar: str) -> None:
        await asyncio.to_thread(self.yol(anahtar).unlink, missing_ok=True)


class R2Depo:
    """Yayın: Cloudflare R2 (S3 uyumlu), özel kova. boto3 eşzamanlı: iş parçacığında."""

    kip = "r2"

    def __init__(
        self,
        *,
        hesap_kimligi: str,
        erisim_anahtari: str,
        gizli_anahtar: str,
        kova: str,
        zaman_asimi_sn: float,
    ) -> None:
        import boto3  # yalnızca R2 kipinde gerekir
        from botocore.config import Config

        self._kova = kova
        self._istemci = boto3.client(
            "s3",
            endpoint_url=f"https://{hesap_kimligi}.r2.cloudflarestorage.com",
            aws_access_key_id=erisim_anahtari,
            aws_secret_access_key=gizli_anahtar,
            region_name="auto",
            config=Config(connect_timeout=zaman_asimi_sn, read_timeout=zaman_asimi_sn),
        )
        sarici = gozlemli("depo")
        sure = zaman_asimli(zaman_asimi_sn * 2)
        self.koy = sarici(sure(self._koy))
        self.al = sarici(sure(self._al))
        self.sil = sarici(sure(self._sil))

    async def _koy(self, anahtar: str, veri: bytes, icerik_turu: str) -> None:
        await asyncio.to_thread(
            self._istemci.put_object,
            Bucket=self._kova,
            Key=_anahtar_gecerli(anahtar),
            Body=veri,
            ContentType=icerik_turu,
        )

    async def _al(self, anahtar: str) -> bytes:
        yanit = await asyncio.to_thread(
            self._istemci.get_object, Bucket=self._kova, Key=_anahtar_gecerli(anahtar)
        )
        return await asyncio.to_thread(yanit["Body"].read)

    async def imzali_adres(self, anahtar: str, *, dosya_adi: str, icerik_turu: str) -> str:
        # İmzalama yereldir, ağ isteği yok.
        return self._istemci.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._kova,
                "Key": _anahtar_gecerli(anahtar),
                "ResponseContentDisposition": indirme_basligi(dosya_adi),
                "ResponseContentType": icerik_turu,
            },
            ExpiresIn=IMZALI_ADRES_SURESI_SN,
        )

    async def _sil(self, anahtar: str) -> None:
        await asyncio.to_thread(
            self._istemci.delete_object, Bucket=self._kova, Key=_anahtar_gecerli(anahtar)
        )


class KapaliDepo:
    """Null Object: dosya yükleme kapalı; yükleme 503, silme sessiz."""

    kip = "kapali"

    async def koy(self, anahtar: str, veri: bytes, icerik_turu: str) -> None:
        raise DepoKapali

    async def al(self, anahtar: str) -> bytes:
        raise DepoKapali

    async def imzali_adres(self, anahtar: str, *, dosya_adi: str, icerik_turu: str) -> str:
        raise DepoKapali

    async def sil(self, anahtar: str) -> None:
        return None
