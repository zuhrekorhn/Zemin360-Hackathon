"""Doğrulama servislerinin ortak veritabanı okumaları.

Ayrı modül, çünkü hem kanıt hem referans servisi kullanıyor; ikisi birbirini
içe aktarmadan aynı okumayı paylaşsın diye (bağımlılık yönü: itiraz → kanit →
referans → sorgular).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.kullanici import Kullanici
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti


class CiktiBulunamadi(LookupError):
    """İş kalemi yok (uçta 404)."""


async def cikti_getir(oturum: AsyncSession, somut_cikti_id: uuid.UUID) -> SomutCikti:
    """İş kalemini güven göstergesi ve referans istekleriyle birlikte okur.

    Sahipliğe bakmaz: girişsiz referans yanıtı da kullanıyor (orada kimlik
    token'ın kendisi). Sahiplik uçların işi (`app/api/sahiplik.py`).
    """
    cikti = await oturum.scalar(
        select(SomutCikti)
        .options(
            selectinload(SomutCikti.guven_skoru),
            selectinload(SomutCikti.referans_istekleri),
            selectinload(SomutCikti.kanit_parcalari),
        )
        .where(SomutCikti.id == somut_cikti_id)
    )
    if cikti is None:
        raise CiktiBulunamadi(somut_cikti_id)
    return cikti


async def gencin_hesap_id(oturum: AsyncSession, yetenek_karti_id: uuid.UUID) -> uuid.UUID | None:
    """Kartın sahibi gencin hesap kimliği (bildirim için)."""
    return await oturum.scalar(
        select(Kullanici.hesap_id)
        .join(YetenekKarti, YetenekKarti.kullanici_id == Kullanici.id)
        .where(YetenekKarti.id == yetenek_karti_id)
    )


async def gencin_adi(oturum: AsyncSession, yetenek_karti_id: uuid.UUID) -> str | None:
    """Kartın sahibi gencin kayıttaki adı (referans e-postası için)."""
    return await oturum.scalar(
        select(Kullanici.ad)
        .join(YetenekKarti, YetenekKarti.kullanici_id == Kullanici.id)
        .where(YetenekKarti.id == yetenek_karti_id)
    )
