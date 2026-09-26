"""Yerel veritabanını boşaltır (docs/faz-b-kimlik-ve-dongu.md § 8).

Uygulama tablolarını ve LangGraph sohbet checkpoint'lerini TRUNCATE eder;
şemaya dokunmaz (alembic_version ve checkpoint_migrations kalır, migration
yeniden çalıştırmak gerekmez). Faz B öncesi, gencin onayı olmadan
`kabul_edildi` olmuş kayıtlar yeni modele uymuyor; tarayıcı denemesi temiz
veriyle başlasın diye.

Onay sorar (veritabanı adını yazdırır); `APP_ENV=production` ise çalışmaz.

    .venv/Scripts/python.exe scripts/yerel_sifirla.py
    .venv/Scripts/python.exe scripts/yerel_sifirla.py --evet   # onay sormadan
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.engine import make_url

import app.models  # noqa: F401  (tüm tablolar metadata'ya kaydolsun)
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_sessionmaker

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# LangGraph'ın Postgres checkpointer'ı (langgraph-checkpoint-postgres).
# `checkpoint_migrations` bilerek yok: o şema sürümünü tutuyor, silinirse
# checkpointer tabloları yeniden kurmaya çalışır.
CHECKPOINT_TABLOLARI = ("checkpoints", "checkpoint_blobs", "checkpoint_writes")
DOKUNULMAYANLAR = ("alembic_version", "checkpoint_migrations")


class UretimdeCalismaz(Exception):
    pass


def calistirilabilir_mi(app_env: str) -> None:
    if app_env.strip().lower() == "production":
        raise UretimdeCalismaz("APP_ENV=production: yerel sıfırlama canlı veritabanında çalışmaz.")


def sifirlanacak_tablolar() -> list[str]:
    """Modellerin tüm tabloları + checkpoint tabloları, isme göre sıralı."""
    return sorted({t.name for t in Base.metadata.sorted_tables} | set(CHECKPOINT_TABLOLARI))


def truncate_ifadesi(tablolar: list[str]) -> str:
    # CASCADE: FK sırasıyla uğraşmadan tek komut; RESTART IDENTITY zararsız
    # (kimlikler UUID, sıra yok) ama ileride eklenecek bir sayaç için doğru olan.
    return f"TRUNCATE {', '.join(tablolar)} RESTART IDENTITY CASCADE"


async def sifirla(tablolar: list[str]) -> None:
    async with get_sessionmaker()() as oturum:
        await oturum.execute(text(truncate_ifadesi(tablolar)))
        await oturum.commit()


def main() -> None:
    ayristirici = argparse.ArgumentParser(description="Yerel veritabanını boşaltır")
    ayristirici.add_argument("--evet", action="store_true", help="onay sormadan çalıştır")
    argumanlar = ayristirici.parse_args()

    ayarlar = get_settings()
    try:
        calistirilabilir_mi(ayarlar.app_env)
    except UretimdeCalismaz as hata:
        raise SystemExit(str(hata)) from hata

    adres = make_url(ayarlar.database_url)
    tablolar = sifirlanacak_tablolar()
    print(f"Veritabanı: {adres.database} @ {adres.host}:{adres.port}")
    print(f"Boşaltılacak {len(tablolar)} tablo: {', '.join(tablolar)}")
    print(f"Dokunulmayacak: {', '.join(DOKUNULMAYANLAR)}")
    if not argumanlar.evet:
        onay = input(f"Devam etmek için veritabanı adını yaz ({adres.database}): ")
        if onay.strip() != adres.database:
            raise SystemExit("Vazgeçildi, hiçbir şey silinmedi.")

    asyncio.run(sifirla(tablolar))
    print("Tamam. Demo hesapları için: scripts/demo_hesaplari.py")


if __name__ == "__main__":
    main()
