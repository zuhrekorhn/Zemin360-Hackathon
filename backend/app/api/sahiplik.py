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

from app.agents.uygunluk import gorunur_kosulu
from app.models.eslesme import Eslesme
from app.models.firma_karti import FirmaKarti
from app.models.hesap import ROL_GENC, ROL_GIRVAK, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.yetenek_karti import YetenekKarti

# Gencin görebildiği eşleşme durumları. Faz B'de genç eşleşmeyi ancak kurum
# ilgilendikten sonra görüyordu; genç akışında (docs/plans/genc-akisi.md § 0,
# karar 1) eşik üstü öneriler gence "fırsat" olarak baştan görünür, yani kendi
# kartının bütün eşleşmeleri. E-posta yine yalnızca karşılıklı ilgide açılır.
GENCE_ACIK_DURUMLAR = (
    "onerildi",
    "genc_ilgilendi",
    "ilgileniliyor",
    "kabul_edildi",
    "reddedildi",
    "kapandi",
)

# Eşleşmenin iki tarafı (docs/plans/firma-akisi.md § 3, karar 12). Durum
# makinesindeki roller bu iki taraftır, hesabın rolü değil: aday tarafı bugün
# yetenek kartının genci, firma–firma eşleşmede aday firma olacak. Değerler
# eski rol adlarıyla aynı: `eslesme.baslatan` ve `gecis()` tablosu değişmesin.
TARAF_ADAY = ROL_GENC
TARAF_ILAN = ROL_KURUM

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
                    gorunur_kosulu(),
                )
            )
        )
    )


# --- Eşleşmenin tarafları ---------------------------------------------------------------


def eslesmedeki_taraf(hesap: Hesap, eslesme: Eslesme) -> str | None:
    """Hesap bu eşleşmenin aday tarafı mı, ilan tarafı mı? Değilse None.

    `eslesme` iki kartıyla ve sahipleriyle yüklenmiş olmalı.
    """
    if eslesme.firma_karti is not None:
        # Firma–firma: aday tarafı firma kartının firması. Kendi firması
        # önerilmediği için bir firma iki tarafta birden olamaz.
        if eslesme.firma_karti.kurum_id == kurum_id(hesap):
            return TARAF_ADAY
    elif yetenek_kartinin_sahibi_mi(hesap, eslesme.yetenek_karti):
        return TARAF_ADAY
    if ihtiyac_kartinin_sahibi_mi(hesap, eslesme.ihtiyac_karti):
        return TARAF_ILAN
    return None


def karsi_taraf(taraf: str) -> str:
    return TARAF_ILAN if taraf == TARAF_ADAY else TARAF_ADAY


def taraf_hesabi(eslesme: Eslesme, taraf: str) -> uuid.UUID | None:
    """Tarafın hesabı (bildirim alıcısı)."""
    if taraf == TARAF_ADAY and eslesme.firma_karti is not None:
        return eslesme.firma_karti.kurum.hesap_id
    if taraf == TARAF_ADAY:
        return eslesme.yetenek_karti.kullanici.hesap_id
    return eslesme.ihtiyac_karti.kurum.hesap_id


def taraf_adi(eslesme: Eslesme, taraf: str) -> str:
    """Tarafın kullanıcıya görünen adı (gencin adı ya da firmanın adı)."""
    if taraf == TARAF_ADAY and eslesme.firma_karti is not None:
        return eslesme.firma_karti.kurum.ad
    if taraf == TARAF_ADAY:
        return eslesme.yetenek_karti.kullanici.ad
    return eslesme.ihtiyac_karti.kurum.ad


def calisma_basligi(eslesme: Eslesme) -> str | None:
    """Genç adayın kartından e-posta taslağında anılacak çalışma: en yeni tarihli, yoksa ilki.

    Yalnızca başlık döner; çalışmaların `somut_ciktilar` ilişkisi yüklü olmalı.
    """
    if eslesme.yetenek_karti is None or not eslesme.yetenek_karti.somut_ciktilar:
        return None
    ciktilar = eslesme.yetenek_karti.somut_ciktilar
    secilen = max(ciktilar, key=lambda c: c.tarih.toordinal() if c.tarih else 0)
    return secilen.baslik


# --- İhtiyaç kartı ---------------------------------------------------------------------


def ihtiyac_kartinin_sahibi_mi(hesap: Hesap, kart: IhtiyacKarti) -> bool:
    return kart.kurum_id == kurum_id(hesap)


async def ihtiyac_kartini_gorebilir_mi(
    oturum: AsyncSession, hesap: Hesap, kart: IhtiyacKarti
) -> bool:
    """Kurum kendi kartını, genç yalnızca kendisine önerilmiş ihtiyacı, GİRVAK hepsini.

    Firma, kendi firma kartına önerilmiş ortak ilanını da görür
    (docs/plans/firma-akisi.md § 0 karar 16).
    """
    if girvak_mi(hesap) or ihtiyac_kartinin_sahibi_mi(hesap, kart):
        return True
    kurumu = kurum_id(hesap)
    if kurumu is not None:
        return bool(
            await oturum.scalar(
                select(
                    exists().where(
                        Eslesme.ihtiyac_karti_id == kart.id,
                        Eslesme.firma_karti_id == FirmaKarti.id,
                        FirmaKarti.kurum_id == kurumu,
                        gorunur_kosulu(),
                    )
                )
            )
        )
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
                    gorunur_kosulu(),
                )
            )
        )
    )
