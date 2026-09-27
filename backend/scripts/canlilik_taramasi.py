"""Canlılık taramasını yerelde çalıştırır (docs/faz-d-canlilik.md § 4).

Canlıda bu işi platform cron'u yapar (`POST /canlilik/tarama`, başlıkta
TARAMA_ANAHTARI); yerelde ve demoda GİRVAK panelindeki düğme ya da bu betik.
Tekrar kuralı gereği art arda çalıştırmak zararsız: ikincisi sıfır olay yazar.

    .venv/Scripts/python.exe scripts/canlilik_taramasi.py
"""

from __future__ import annotations

import asyncio
import sys

from app.api.canlilik import tarama_yap
from app.db.session import get_sessionmaker

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def calistir() -> None:
    async with get_sessionmaker()() as oturum:
        sonuc = await tarama_yap(oturum)
    print(f"Tarama tamam ({sonuc.sure_sn} sn): {sonuc.bildirim} bildirim")
    if not sonuc.olaylar:
        print("  Yeni hatırlatma yok (eşiği aşan kayıt yok ya da bu dönemde zaten hatırlatıldı).")
    for tur, sayi in sorted(sonuc.olaylar.items()):
        print(f"  {tur}: {sayi} olay")


if __name__ == "__main__":
    asyncio.run(calistir())
