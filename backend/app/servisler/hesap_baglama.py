"""Hesap bağlama: OAuth ve doğrulama kodu (docs/plans/dogrulama-iyilestirme.md § 6).

Bağlı hesaptaki çalışma seviye B'dir (`agents/dogrulama/hesap_sahipligi.py`).
Bağlantı değişince gencin linkli çalışmaları arka planda yeniden okunur
(`kart_hazirlama.kalemleri_yeniden_oku`): seviyesi değişmeyen kalemde önbellek
tutar, model çağrılmaz.

OAuth akışı iki adımdır ve backend'de oturum tutmaz:
  1. `oauth_baslat`: imzalı, 10 dakikalık `durum` (hesap + sağlayıcı) ile
     sağlayıcının yetki adresi. Frontend kullanıcıyı oraya yönlendirir.
  2. Sağlayıcı frontend'e döner (`/hesap-baglama/{saglayici}`); frontend kodu
     ve durumu giriş yapmış kullanıcının token'ıyla `oauth_tamamla`'ya iletir.
     Durum başka bir hesaba aitse ret (CSRF): bağlantıyı başlatan bitirir.

Sözleşme diğer servislerle aynı: model değişir; commit, arka plan işi ve HTTP'ye
çeviri çağıranın işidir.
"""

from __future__ import annotations

import datetime as dt
import secrets
import uuid

import jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dis_servisler import kurulum
from app.core.dis_servisler.oauth import DisHesap, OAuthReddedildi, OAuthSaglayici
from app.core.kimlik import ALGORITMA
from app.models.bagli_hesap import BagliHesap

DURUM_OMRU = dt.timedelta(minutes=10)
_DURUM_AMACI = "hesap_baglama"


class SaglayiciKapali(LookupError):
    """Sağlayıcı tanımsız ya da ayarı yok (uçta 404)."""


class DurumGecersiz(ValueError):
    """Dönüşteki durum imzasız, süresi dolmuş ya da başka hesaba / sağlayıcıya ait."""


class BaglantiReddedildi(ValueError):
    """Sağlayıcı kodu kabul etmedi; genç yeniden başlatmalı."""


class BaskasinaBagli(Exception):
    """Bu platform hesabı başka bir gence bağlı (uçta 409)."""


class BagliHesapBulunamadi(LookupError):
    """Yok ya da başkasının (uçta 404: varlık sızmasın)."""


# --- OAuth ---------------------------------------------------------------------------------


def acik_oauth_saglayicilari() -> list[str]:
    return sorted(kurulum.oauth_saglayicilari())


def _saglayici(ad: str) -> OAuthSaglayici:
    saglayici = kurulum.oauth_saglayicilari().get(ad)
    if saglayici is None:
        raise SaglayiciKapali(ad)
    return saglayici


def donus_adresi(saglayici: str) -> str:
    """Sağlayıcıda kayıtlı dönüş adresiyle birebir aynı olmalı."""
    return f"{get_settings().uygulama_adresi}/hesap-baglama/{saglayici}"


def _durum_uret(hesap_id: uuid.UUID, saglayici: str) -> str:
    simdi = dt.datetime.now(dt.UTC)
    icerik = {
        "amac": _DURUM_AMACI,
        "sub": str(hesap_id),
        "saglayici": saglayici,
        # Aynı saniyede iki başlatma aynı durumu üretmesin.
        "nonce": secrets.token_urlsafe(8),
        "exp": simdi + DURUM_OMRU,
    }
    return jwt.encode(icerik, get_settings().jwt_gizli_anahtar, algorithm=ALGORITMA)


def _durumu_dogrula(durum: str, hesap_id: uuid.UUID, saglayici: str) -> None:
    try:
        icerik = jwt.decode(
            durum,
            get_settings().jwt_gizli_anahtar,
            algorithms=[ALGORITMA],
            options={"require": ["amac", "sub", "saglayici", "exp"]},
        )
    except jwt.PyJWTError as hata:
        raise DurumGecersiz(str(hata)) from hata
    if (icerik["amac"], icerik["sub"], icerik["saglayici"]) != (
        _DURUM_AMACI,
        str(hesap_id),
        saglayici,
    ):
        raise DurumGecersiz("durum bu hesaba ya da sağlayıcıya ait değil")


def oauth_baslat(hesap_id: uuid.UUID, saglayici: str) -> str:
    """Kullanıcının yönlendirileceği yetki adresi."""
    return _saglayici(saglayici).yetki_adresi(
        _durum_uret(hesap_id, saglayici), donus_adresi(saglayici)
    )


async def oauth_tamamla(
    oturum: AsyncSession,
    *,
    hesap_id: uuid.UUID,
    kullanici_id: uuid.UUID,
    saglayici: str,
    kod: str,
    durum: str,
) -> BagliHesap:
    """Kodu kimliğe çevirir ve hesabı bağlar. Token saklanmaz (§ 6.1).

    Sağlayıcıya ulaşılamazsa (zaman aşımı, ağ) `TimeoutError` / `httpx.HTTPError`
    çağırana çıkar (uçta 503).
    """
    istemci = _saglayici(saglayici)
    _durumu_dogrula(durum, hesap_id, saglayici)
    try:
        dis = await istemci.hesabi_oku(kod, donus_adresi(saglayici))
    except OAuthReddedildi as hata:
        raise BaglantiReddedildi(saglayici) from hata
    return await bagla(oturum, kullanici_id, saglayici, dis, yontem="oauth")


# --- Ortak ---------------------------------------------------------------------------------


async def bagla(
    oturum: AsyncSession,
    kullanici_id: uuid.UUID,
    saglayici: str,
    dis: DisHesap,
    *,
    yontem: str,
) -> BagliHesap:
    """Hesabı gence bağlar. Aynı gencin aynı hesabı yeniden bağlaması yan etkisizdir
    (görünen ad tazelenir); başka gence bağlı hesap 409."""
    mevcut = await oturum.scalar(
        select(BagliHesap).where(
            BagliHesap.saglayici == saglayici, BagliHesap.dis_kimlik == dis.dis_kimlik
        )
    )
    if mevcut is not None:
        if mevcut.kullanici_id != kullanici_id:
            raise BaskasinaBagli(saglayici)
        mevcut.kullanici_adi = dis.kullanici_adi
        return mevcut
    hesap = BagliHesap(
        kullanici_id=kullanici_id,
        saglayici=saglayici,
        kullanici_adi=dis.kullanici_adi,
        dis_kimlik=dis.dis_kimlik,
        yontem=yontem,
    )
    try:
        async with oturum.begin_nested():
            oturum.add(hesap)
            await oturum.flush()
    except IntegrityError as hata:
        # Aynı anda iki gencin aynı hesabı bağlaması: tekil kısıt karar verir.
        raise BaskasinaBagli(saglayici) from hata
    return hesap


async def bagli_hesaplar(oturum: AsyncSession, kullanici_id: uuid.UUID) -> list[BagliHesap]:
    return list(
        await oturum.scalars(
            select(BagliHesap)
            .where(BagliHesap.kullanici_id == kullanici_id)
            .order_by(BagliHesap.baglanma_tarihi)
        )
    )


async def baglantiyi_kaldir(
    oturum: AsyncSession, kullanici_id: uuid.UUID, bagli_hesap_id: uuid.UUID
) -> None:
    hesap = await oturum.get(BagliHesap, bagli_hesap_id)
    if hesap is None or hesap.kullanici_id != kullanici_id:
        raise BagliHesapBulunamadi(bagli_hesap_id)
    await oturum.delete(hesap)
