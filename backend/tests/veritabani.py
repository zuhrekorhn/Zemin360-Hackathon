"""Gerçek yerel veritabanında, sonunda geri alınan bir işlem içinde test.

Uç nokta `commit()` etse bile hiçbir şey kalıcı olmaz: oturum dış işleme
savepoint'le katılır, test bitince dış işlem geri alınır. Yerel veritabanı
yoksa (ya da .env'de adres yoksa) test atlanır.

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            yanit = await istemci.post("/auth/kayit", json={...})

    asyncio.run(senaryo())
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

import asyncpg
import httpx
import pytest
from dotenv import dotenv_values
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.session import get_session
from app.main import app


def veritabani_adresi() -> str | None:
    adres = dotenv_values(".env").get("DATABASE_URL")
    if not adres:
        return None
    return adres.replace("postgresql://", "postgresql+asyncpg://", 1)


@contextlib.asynccontextmanager
async def geri_alinan_oturum() -> AsyncIterator[AsyncSession]:
    adres = veritabani_adresi()
    if adres is None:
        pytest.skip("Yerel veritabanı tanımlı değil (.env)")
    motor = create_async_engine(adres, poolclass=NullPool)
    try:
        baglanti = await motor.connect()
    except (OSError, asyncpg.PostgresError) as hata:
        await motor.dispose()
        pytest.skip(f"Yerel veritabanına ulaşılamadı: {hata}")

    dis_islem = await baglanti.begin()
    oturum = AsyncSession(
        bind=baglanti, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield oturum
    finally:
        await oturum.close()
        await dis_islem.rollback()
        await baglanti.close()
        await motor.dispose()


@contextlib.asynccontextmanager
async def api_istemcisi(oturum: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    """Uygulamayı aynı olay döngüsünde, verilen oturumla çağıran istemci."""
    app.dependency_overrides[get_session] = lambda: oturum
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as istemci:
            yield istemci
    finally:
        app.dependency_overrides.pop(get_session, None)
