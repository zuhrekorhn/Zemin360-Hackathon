"""GİRVAK hesabı açar (docs/kimlik-ve-dongu.md § 2).

GİRVAK açık kayıtla hesap açamaz; hesap bu betikle ya da demo tohumuyla açılır.
Şifre komut satırında sorulur, hiçbir dosyaya yazılmaz.

    .venv/Scripts/python.exe scripts/girvak_hesabi.py --email girvak@ornek.org
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from app.api.auth import EpostaKayitli, hesap_olustur
from app.core.kimlik import SIFRE_EN_AZ
from app.db.session import get_sessionmaker
from app.models.hesap import ROL_GIRVAK

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def sifre_sor() -> str:
    sifre = getpass.getpass("Şifre: ")
    if len(sifre) < SIFRE_EN_AZ:
        raise SystemExit(f"Şifre en az {SIFRE_EN_AZ} karakter olmalı.")
    if getpass.getpass("Şifre (tekrar): ") != sifre:
        raise SystemExit("Şifreler aynı değil.")
    return sifre


async def ac(email: str, sifre: str) -> None:
    async with get_sessionmaker()() as oturum:
        try:
            hesap = await hesap_olustur(
                oturum, email=email, sifre=sifre, rol=ROL_GIRVAK, ad=None, eposta_dogrulandi=True
            )
        except EpostaKayitli as hata:
            raise SystemExit(f"{email} ile bir hesap zaten var.") from hata
    print(f"GİRVAK hesabı açıldı: {hesap.email} ({hesap.id})")


def main() -> None:
    ayristirici = argparse.ArgumentParser(description="GİRVAK hesabı açar")
    ayristirici.add_argument("--email", required=True)
    argumanlar = ayristirici.parse_args()
    asyncio.run(ac(argumanlar.email, sifre_sor()))


if __name__ == "__main__":
    main()
