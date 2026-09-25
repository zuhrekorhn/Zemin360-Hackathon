"""Kaynak sahipliği: kim hangi kartı, eşleşmeyi, sohbeti görebilir ya da değiştirebilir.

Kuralların tablosu: docs/faz-b-kimlik-ve-dongu.md § 3. Uç noktalar kaynağı
okuyup buradaki fonksiyonlara sorar; tek kaynak burası.

Hata kodu sözleşmesi:
  401 — token yok/geçersiz (app/api/kimlik.py › mevcut_hesap)
  403 — rol uygun değil (app/api/kimlik.py › rol_gerekli)
  404 — başkasının kaynağı. 403 değil: kaynağın var olduğu sızmasın.

GİRVAK okuma işlerinde her şeyi görür; yazma işleri genç ve kurumun işidir.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.eslesme import Eslesme
from app.models.hesap import ROL_GENC, ROL_GIRVAK, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.yetenek_karti import YetenekKarti

# Gencin ihtiyaç kartını görebilmesi için eşleşmenin ulaşmış olması gereken
# durumlar: kurum ilgilendikten sonra (not § 3). "onerildi" iken genç kurumun
# kendisine bakıp bakmadığını bilmez.
GENCE_ACIK_DURUMLAR = ("ilgileniliyor", "kabul_edildi", "reddedildi")

# Sohbet checkpoint'ine oturumu açan hesabın kimliği bu anahtarla yazılır.
SOHBET_SAHIBI = "sahip_hesap_id"


def bulunamadi(mesaj: str) -> HTTPException:
    return HTTPException(status_code=404, detail=mesaj)


def girvak_mi(hesap: Hesap) -> bool:
    return hesap.rol == ROL_GIRVAK


def kullanici_id(hesap: Hesap) -> uuid.UUID | None:
    return hesap.kullanici.id if hesap.rol == ROL_GENC and hesap.kullanici else None


def kurum_id(hesap: Hesap) -> uuid.UUID | None:
    return hesap.kurum.id if hesap.rol == ROL_KURUM and hesap.kurum else None


# --- Sohbet oturumları ---------------------------------------------------------------


def sohbet_baslangici(hesap: Hesap) -> dict[str, str]:
    """Sohbet açılırken grafiğe verilen girdi: oturum kimin?"""
    return {SOHBET_SAHIBI: str(hesap.id)}


def sohbetin_sahibi_mi(degerler: dict[str, Any], hesap: Hesap) -> bool:
    """Checkpoint'teki sohbeti bu hesap mı açtı? Faz B öncesi sohbetlerin sahibi yok."""
    return degerler.get(SOHBET_SAHIBI) == str(hesap.id)


# --- Yetenek kartı ---------------------------------------------------------------------


def yetenek_kartinin_sahibi_mi(hesap: Hesap, kart: YetenekKarti) -> bool:
    return kart.kullanici_id is not None and kart.kullanici_id == kullanici_id(hesap)


async def yetenek_kartini_gorebilir_mi(
    oturum: AsyncSession, hesap: Hesap, kart: YetenekKarti
) -> bool:
    """Genç kendi kartını, kurum yalnızca kendisine önerilmiş kartı, GİRVAK hepsini."""
    if girvak_mi(hesap) or yetenek_kartinin_sahibi_mi(hesap, kart):
        return True
    kurumu = kurum_id(hesap)
    if kurumu is None:
        return False
    return bool(
        await oturum.scalar(
            select(
                exists().where(
                    Eslesme.yetenek_karti_id == kart.id,
                    Eslesme.ihtiyac_karti_id == IhtiyacKarti.id,
                    IhtiyacKarti.kurum_id == kurumu,
                )
            )
        )
    )


# --- İhtiyaç kartı ---------------------------------------------------------------------


def ihtiyac_kartinin_sahibi_mi(hesap: Hesap, kart: IhtiyacKarti) -> bool:
    return kart.kurum_id == kurum_id(hesap)


async def ihtiyac_kartini_gorebilir_mi(
    oturum: AsyncSession, hesap: Hesap, kart: IhtiyacKarti
) -> bool:
    """Kurum kendi kartını, genç yalnızca kendisine ilgi gösterilmiş ihtiyacı, GİRVAK hepsini."""
    if girvak_mi(hesap) or ihtiyac_kartinin_sahibi_mi(hesap, kart):
        return True
    gencin = kullanici_id(hesap)
    if gencin is None:
        return False
    return bool(
        await oturum.scalar(
            select(
                exists().where(
                    Eslesme.ihtiyac_karti_id == kart.id,
                    Eslesme.yetenek_karti_id == YetenekKarti.id,
                    YetenekKarti.kullanici_id == gencin,
                    Eslesme.durum.in_(GENCE_ACIK_DURUMLAR),
                )
            )
        )
    )
