"""Kayıt e-postasının doğrulanması (docs/plans/dogrulama-iyilestirme.md § 6.3, bulgu 37).

Akış: kayıt → `baglanti_olustur` (aynı istekte) → e-posta yanıttan sonra gider
(`epostayi_gonder`, arka plan; hatası kaydı düşürmez) → kullanıcı bağlantıyı
açar → `dogrula`. Doğrulama girişi ya da başka bir akışı engellemez; tek etkisi
gencin adını kilitlemek ve ada dayalı seviye A koşulunu açmaktır.

Sözleşme (diğer servislerle aynı): model değişir, commit ve HTTP'ye çeviri
çağıranın işidir.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import secrets
from urllib.parse import quote

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dis_servisler import Eposta, dusmeden_gonder, kurulum
from app.models.eposta_dogrulama import EpostaDogrulama
from app.models.hesap import ROL_KURUM, Hesap

GECERLILIK = dt.timedelta(hours=24)
# Yeni bağlantı isteği bundan sık olamaz (art arda tıklama e-posta yağdırmasın).
YENIDEN_GONDERME_ARALIGI = dt.timedelta(minutes=1)


class BaglantiGecersiz(Exception):
    """Bağlantı yok ya da süresi dolmuş. Mesaj kullanıcıya gösterilir."""


class ZatenDogrulandi(Exception):
    """Hesabın e-postası zaten doğrulanmış (yeniden gönderme isteği)."""


class CokSikIstek(Exception):
    """Yeni bağlantı için biraz beklenmeli. Mesaj kullanıcıya gösterilir."""


def _ozet(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _simdi() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def dogrulandi_mi(hesap: Hesap) -> bool:
    return hesap.eposta_dogrulandi_tarihi is not None


async def baglanti_olustur(oturum: AsyncSession, hesap: Hesap) -> str:
    """Yeni bağlantının token'ını döner; hesabın eski bağlantıları geçersiz olur."""
    await oturum.execute(delete(EpostaDogrulama).where(EpostaDogrulama.hesap_id == hesap.id))
    token = secrets.token_urlsafe(32)
    oturum.add(
        EpostaDogrulama(
            hesap_id=hesap.id, token_ozeti=_ozet(token), son_gecerlilik=_simdi() + GECERLILIK
        )
    )
    return token


async def yeniden_baglanti_olustur(oturum: AsyncSession, hesap: Hesap) -> str:
    if dogrulandi_mi(hesap):
        raise ZatenDogrulandi
    son = await oturum.scalar(
        select(EpostaDogrulama.olusturma_tarihi)
        .where(EpostaDogrulama.hesap_id == hesap.id)
        .order_by(EpostaDogrulama.olusturma_tarihi.desc())
        .limit(1)
    )
    if son is not None and _simdi() - son < YENIDEN_GONDERME_ARALIGI:
        raise CokSikIstek("Bağlantı az önce gönderildi. Bir dakika sonra yeniden deneyebilirsin.")
    return await baglanti_olustur(oturum, hesap)


async def dogrula(oturum: AsyncSession, token: str) -> Hesap:
    """Bağlantı geçerliyse hesabı doğrular. Aynı bağlantının tekrarı yan etkisiz."""
    kayit = await oturum.scalar(
        select(EpostaDogrulama).where(EpostaDogrulama.token_ozeti == _ozet(token))
    )
    if kayit is None or kayit.son_gecerlilik <= _simdi():
        raise BaglantiGecersiz(
            "Bu bağlantı geçersiz ya da süresi dolmuş. Giriş yapıp yeni bağlantı isteyebilirsin."
        )
    hesap = await oturum.get(Hesap, kayit.hesap_id, with_for_update=True)
    if hesap.eposta_dogrulandi_tarihi is None:
        hesap.eposta_dogrulandi_tarihi = _simdi()
    return hesap


def dogrulama_epostasi(hesap: Hesap, token: str) -> Eposta:
    """Hitap rehbere göre: firmaya "siz", gence "sen" (docs/icerik-rehberi.md)."""
    baglanti = f"{get_settings().uygulama_adresi.rstrip('/')}/eposta-dogrula?token={quote(token)}"
    if hesap.rol == ROL_KURUM:
        konu = "Zemin360: e-posta adresinizi doğrulayın"
        metin = (
            "Merhaba,\n\n"
            "Zemin360 hesabınızın e-posta adresini doğrulamak için bu bağlantıyı açın:\n"
            f"{baglanti}\n\n"
            "Bağlantı 24 saat geçerli. Bu hesabı siz açmadıysanız bu e-postayı yok sayabilirsiniz."
        )
    else:
        konu = "Zemin360: e-posta adresini doğrula"
        metin = (
            "Merhaba,\n\n"
            "Zemin360 hesabının e-posta adresini doğrulamak için bu bağlantıyı aç:\n"
            f"{baglanti}\n\n"
            "Bağlantı 24 saat geçerli. Bu hesabı sen açmadıysan bu e-postayı yok sayabilirsin."
        )
    return Eposta(alici=hesap.email, konu=konu, metin=metin)


async def epostayi_gonder(eposta: Eposta) -> None:
    """Arka plan işi: yanıttan sonra gönderir; hata kaydı ya da isteği düşürmez (İ9)."""
    await dusmeden_gonder(kurulum.eposta_gonderici(), eposta)
