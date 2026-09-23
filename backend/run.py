"""Geliştirme sunucusu başlatıcısı.

Neden `uvicorn app.main:app` yerine bu: LangGraph'ın Postgres checkpointer'ı
psycopg kullanıyor ve psycopg async, Windows'un varsayılan ProactorEventLoop'u
ile çalışmıyor. uvicorn ise Windows'ta (`--reload` verilmediği sürece) tam da
o döngüyü seçiyor — sonuç: uygulama açılışta "Psycopg cannot use the
'ProactorEventLoop'" hatasıyla düşüyor.

Burada döngüyü açıkça SelectorEventLoop'a sabitliyoruz. Linux/macOS'ta
davranış değişmez.

    python run.py                 # http://localhost:8000
    python run.py --port 8001     # farklı port
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import uvicorn


def main() -> None:
    ayristirici = argparse.ArgumentParser(description="Zemin360 API geliştirme sunucusu")
    ayristirici.add_argument("--host", default="127.0.0.1")
    ayristirici.add_argument("--port", type=int, default=8000)
    ayristirici.add_argument("--reload", action="store_true", help="kod değişince yeniden başlat")
    argumanlar = ayristirici.parse_args()

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    if argumanlar.reload:
        # reload alt süreç kullanıyor; uvicorn o durumda zaten SelectorEventLoop seçiyor.
        uvicorn.run("app.main:app", host=argumanlar.host, port=argumanlar.port, reload=True)
        return

    sunucu = uvicorn.Server(
        uvicorn.Config("app.main:app", host=argumanlar.host, port=argumanlar.port)
    )
    asyncio.run(sunucu.serve())


if __name__ == "__main__":
    main()
