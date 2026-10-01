"""Hesap bağlama: OAuth ve doğrulama kodu (docs/plans/dogrulama-iyilestirme.md § 6).

Doğrulama kodu (§ 6.2): genç kodu profil açıklamasına yazar, `kodu_dogrula`
profili okur. Kod bulunursa bağlanır; profil okunamazsa (bot engeli, giriş
duvarı) GİRVAK elle doğrular (`profil_kodu_elle` işareti, `ProfilKoduIsleyici`).
Ekran görüntüsüyle doğrulama yok.

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

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.inceleme_durumu import ACIK, KAPANDI
from app.core.config import get_settings
from app.core.dis_servisler import kurulum
from app.core.dis_servisler.oauth import DisHesap, OAuthReddedildi, OAuthSaglayici
from app.core.kanit_okuma.belge import ErisimDurumu
from app.core.kimlik import ALGORITMA
from app.core.profil_kodu import ProfilKoduPlatformu, kod_geciyor_mu, kod_uret
from app.models.bagli_hesap import BagliHesap, ProfilKodu
from app.models.bildirim import TUR_HESAP_BAGLAMA_SONUCU
from app.models.inceleme_isareti import TUR_PROFIL_KODU_ELLE, IncelemeIsareti
from app.servisler import inceleme, kart_hazirlama
from app.servisler.genc_karti import gencin_karti

DURUM_OMRU = dt.timedelta(minutes=10)
KOD_OMRU = dt.timedelta(hours=48)

# Bildirim metinlerinde platformun adı (gence görünür).
PLATFORM_ADLARI = {
    "github": "GitHub",
    "gitlab": "GitLab",
    "orcid": "ORCID",
    "youtube": "YouTube",
    "kaggle": "Kaggle",
    "behance": "Behance",
    "dribbble": "Dribbble",
    "medium": "Medium",
    "vimeo": "Vimeo",
    "soundcloud": "SoundCloud",
    "kisisel_site": "kişisel site",
}
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


class PlatformBilinmiyor(LookupError):
    """Doğrulama koduyla bağlanamayan platform (uçta 404)."""


class ProfilAdresiGecersiz(ValueError):
    """Adres bu platformda bir profil adresi değil (uçta 422)."""


class KodYok(LookupError):
    """Bu platform için alınmış kod yok (uçta 404)."""


class KodSuresiDoldu(Exception):
    """48 saat geçti; yeni kod alınmalı (uçta 409)."""


class KodBulunamadi(ValueError):
    """Profil okundu ama kod yok (uçta 422)."""


class ProfilBulunamadi(ValueError):
    """Profil adresinde sayfa yok (uçta 422)."""


class BaskaIncelemeBekliyor(Exception):
    """Başka bir platform zaten GİRVAK incelemesinde (uçta 409)."""


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


# --- Doğrulama kodu ------------------------------------------------------------------------


def profil_kodu_platformlari() -> list[str]:
    return sorted(kurulum.profil_kodu_platformlari())


def _platform(ad: str) -> ProfilKoduPlatformu:
    platform = kurulum.profil_kodu_platformlari().get(ad)
    if platform is None:
        raise PlatformBilinmiyor(ad)
    return platform


async def kod_al(
    oturum: AsyncSession, kullanici_id: uuid.UUID, platform: str, profil_adresi: str
) -> ProfilKodu:
    """Yeni kod üretir; aynı platformdaki eski kodun yerine geçer (§ 6.2)."""
    profil = _platform(platform).profil(profil_adresi)
    if profil is None:
        raise ProfilAdresiGecersiz(profil_adresi)
    kayit = await _kod_kaydi(oturum, kullanici_id, platform)
    if kayit is None:
        kayit = ProfilKodu(kullanici_id=kullanici_id, platform=platform)
        oturum.add(kayit)
    kayit.kod = kod_uret()
    kayit.profil_adresi = profil.adres
    kayit.son_gecerlilik = dt.datetime.now(dt.UTC) + KOD_OMRU
    await oturum.flush()
    return kayit


async def bekleyen_kodlar(oturum: AsyncSession, kullanici_id: uuid.UUID) -> list[ProfilKodu]:
    """Süresi dolmamış kodlar (bağlanınca kod silinir)."""
    return list(
        await oturum.scalars(
            select(ProfilKodu)
            .where(
                ProfilKodu.kullanici_id == kullanici_id,
                ProfilKodu.son_gecerlilik > dt.datetime.now(dt.UTC),
            )
            .order_by(ProfilKodu.platform)
        )
    )


async def _kod_kaydi(
    oturum: AsyncSession, kullanici_id: uuid.UUID, platform: str
) -> ProfilKodu | None:
    return await oturum.scalar(
        select(ProfilKodu)
        .where(ProfilKodu.kullanici_id == kullanici_id, ProfilKodu.platform == platform)
        .with_for_update()
    )


async def kodu_dogrula(
    oturum: AsyncSession,
    kullanici_id: uuid.UUID,
    platform: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> BagliHesap | None:
    """Profili okur. Döner: bağlı hesap; ya da None (profil okunamadı, GİRVAK
    elle doğrulayacak). Kod bulunamazsa ya da profil yoksa hata."""
    kayit = await _kod_kaydi(oturum, kullanici_id, platform)
    if kayit is None:
        raise KodYok(platform)
    if kayit.son_gecerlilik <= dt.datetime.now(dt.UTC):
        raise KodSuresiDoldu(platform)
    strateji = _platform(platform)
    profil = strateji.profil(kayit.profil_adresi)
    if profil is None:  # platform kuralı değişmiş; eski kayıt
        raise ProfilAdresiGecersiz(kayit.profil_adresi)
    okuma = await strateji.oku(profil, transport)
    if okuma.metin and kod_geciyor_mu(kayit.kod, okuma.metin):
        dis = DisHesap(profil.kullanici_adi, okuma.dis_kimlik or profil.dis_kimlik)
        bagli = await bagla(oturum, kullanici_id, platform, dis, yontem="profil_kodu")
        await oturum.delete(kayit)
        return bagli
    if okuma.erisim is ErisimDurumu.ACIK:
        raise KodBulunamadi(platform)
    if okuma.erisim in (ErisimDurumu.BULUNAMADI, ErisimDurumu.GUVENSIZ):
        raise ProfilBulunamadi(platform)
    await _elle_dogrulamaya_gonder(
        oturum, kullanici_id, kayit, profil.kullanici_adi, profil.dis_kimlik
    )
    return None


async def _elle_dogrulamaya_gonder(
    oturum: AsyncSession,
    kullanici_id: uuid.UUID,
    kayit: ProfilKodu,
    kullanici_adi: str,
    dis_kimlik: str,
) -> None:
    """Tek açık elle inceleme: aynı platformda yeniden denemek ayrıntıyı tazeler,
    başka platform 409 (tek karar iki hesabı birden onaylamasın)."""
    ayrinti = {
        "platform": kayit.platform,
        "profil_adresi": kayit.profil_adresi,
        "kod": kayit.kod,
        "kullanici_adi": kullanici_adi,
        "dis_kimlik": dis_kimlik,
    }
    acik = await inceleme.acik_isaret(oturum, TUR_PROFIL_KODU_ELLE, kullanici_id)
    if acik is not None and acik.ayrinti.get("platform") != kayit.platform:
        raise BaskaIncelemeBekliyor(acik.ayrinti.get("platform"))
    await inceleme.isaret_ac(
        oturum,
        TUR_PROFIL_KODU_ELLE,
        kullanici_id,
        ayrinti=ayrinti,
        birlestir=lambda _eski, yeni: yeni,
    )


async def inceleme_bekleyen_platform(oturum: AsyncSession, kullanici_id: uuid.UUID) -> str | None:
    """GİRVAK'ın elle doğrulamasını bekleyen platform (yoksa None)."""
    isaret = await oturum.scalar(
        select(IncelemeIsareti).where(
            IncelemeIsareti.tur == TUR_PROFIL_KODU_ELLE,
            IncelemeIsareti.kullanici_id == kullanici_id,
            IncelemeIsareti.durum == ACIK,
        )
    )
    return isaret.ayrinti.get("platform") if isaret is not None else None


class ProfilKoduIsleyici:
    """GİRVAK profilde kodu gördüyse ("sorun yok") hesap `elle` yöntemiyle bağlanır
    ve linkli çalışmalar yeniden okunur; görmediyse bağlanmaz."""

    async def uygula(
        self, oturum: AsyncSession, isaret: IncelemeIsareti, karar: str
    ) -> inceleme.KararEtkisi:
        ayrinti = isaret.ayrinti
        ad = PLATFORM_ADLARI.get(ayrinti["platform"], ayrinti["platform"])
        not_eki = f" GİRVAK'ın notu: {isaret.girvak_notu}" if isaret.girvak_notu else ""

        def etki(metin: str, *isler: inceleme.ArkaPlanIsi) -> inceleme.KararEtkisi:
            return inceleme.KararEtkisi(TUR_HESAP_BAGLAMA_SONUCU, metin + not_eki, isler)

        if karar != KAPANDI:
            return etki(f"{ad} hesabındaki doğrulama kodunu göremedik; hesabın bağlanmadı.")
        dis = DisHesap(ayrinti["kullanici_adi"], ayrinti["dis_kimlik"])
        try:
            await bagla(oturum, isaret.kullanici_id, ayrinti["platform"], dis, yontem="elle")
        except BaskasinaBagli:
            return etki(f"{ad} hesabın başka bir kullanıcıya bağlı olduğu için bağlanamadı.")
        kayit = await _kod_kaydi(oturum, isaret.kullanici_id, ayrinti["platform"])
        if kayit is not None:
            await oturum.delete(kayit)
        kart = await gencin_karti(oturum, isaret.kullanici_id)
        if kart is None:
            return etki(f"{ad} hesabın doğrulandı ve bağlandı.")
        is_ = inceleme.ArkaPlanIsi(kart_hazirlama.kalemleri_yeniden_oku, (kart.id,))
        return etki(f"{ad} hesabın doğrulandı ve bağlandı.", is_)
