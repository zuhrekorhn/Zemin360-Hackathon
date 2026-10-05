"""Dış servislerin tek kurulum noktası (plan § 14.2, bağımlılığın tersine çevrilmesi).

Servisler somut sınıfı tanımaz; buradaki fabrikadan alır. Hangi sınıfın
seçileceği `.env` bayraklarına bağlıdır. Testler fabrikayı sahteyle değiştirir
(`tests/conftest.py`). Yeni bir servis (depo, virüs tarayıcı…) buraya bir
fabrika ve `servis_kipleri`'ne bir satır olarak eklenir.
"""

from __future__ import annotations

import hashlib
import logging
from functools import lru_cache
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.dis_servisler.depo import Depo, KapaliDepo, R2Depo, YerelDepo
from app.core.dis_servisler.eposta import (
    EpostaGonderici,
    KapaliGonderici,
    LogGonderici,
    ResendGonderici,
)
from app.core.dis_servisler.oauth import (
    GithubOAuth,
    GitlabOAuth,
    OAuthAyari,
    OAuthSaglayici,
    OrcidOAuth,
)
from app.core.dis_servisler.virus import ClamavTarayici, KapaliTarayici, VirusTarayici
from app.core.dis_servisler.yedek_okuyucu import (
    KapaliYedekOkuyucu,
    PlaywrightYedekOkuyucu,
    YedekOkuyucu,
)
from app.core.profil_kodu import (
    KisiselSitePlatformu,
    ProfilKoduPlatformu,
    YoutubePlatformu,
    sayfa_platformlari,
)

logger = logging.getLogger("zemin360.dis_servisler")


@lru_cache
def eposta_gonderici() -> EpostaGonderici:
    return eposta_gondericisi_sec(get_settings())


def eposta_gondericisi_sec(ayar: Settings) -> EpostaGonderici:
    if ayar.eposta_saglayici == "kapali":
        return KapaliGonderici()
    if ayar.eposta_saglayici == "resend":
        if ayar.resend_api_key and ayar.eposta_gonderen:
            return ResendGonderici(
                api_anahtari=ayar.resend_api_key,
                gonderen=ayar.eposta_gonderen,
                zaman_asimi_sn=ayar.eposta_zaman_asimi_sn,
            )
        # Eksik ayarla açılış durmaz (İ9): kayıt sürer, bağlantı log'da görünür.
        logger.warning(
            "EPOSTA_SAGLAYICI=resend ama RESEND_API_KEY ya da EPOSTA_GONDEREN boş; log kipi"
        )
    return LogGonderici()


@lru_cache
def oauth_saglayicilari() -> dict[str, OAuthSaglayici]:
    return oauth_saglayicilarini_sec(get_settings())


def oauth_saglayicilarini_sec(ayar: Settings) -> dict[str, OAuthSaglayici]:
    """Kimliği ve gizli anahtarı verilmiş sağlayıcılar; diğerleri kapalı (Null Object
    yerine yokluk: kapalı sağlayıcı arayüzde görünmez, uç 404 döner)."""
    tanimlar = (
        (GithubOAuth, ayar.github_oauth_istemci, ayar.github_oauth_gizli),
        (GitlabOAuth, ayar.gitlab_oauth_istemci, ayar.gitlab_oauth_gizli),
        (OrcidOAuth, ayar.orcid_oauth_istemci, ayar.orcid_oauth_gizli),
    )
    return {
        sinif.saglayici: sinif(OAuthAyari(istemci, gizli, ayar.oauth_zaman_asimi_sn))
        for sinif, istemci, gizli in tanimlar
        if istemci and gizli
    }


@lru_cache
def profil_kodu_platformlari() -> dict[str, ProfilKoduPlatformu]:
    yedek = yedek_okuyucu()
    platformlar: list[ProfilKoduPlatformu] = [
        YoutubePlatformu(get_settings().youtube_api_anahtari, yedek),
        *sayfa_platformlari(yedek),
        KisiselSitePlatformu(yedek),
    ]
    return {p.platform: p for p in platformlar}


@lru_cache
def depo() -> Depo:
    return depo_sec(get_settings())


def depo_sec(ayar: Settings) -> Depo:
    if ayar.depo_saglayici == "r2":
        alanlar = (ayar.r2_hesap_kimligi, ayar.r2_erisim_anahtari, ayar.r2_gizli_anahtar)
        if all(alanlar) and ayar.r2_kova:
            return R2Depo(
                hesap_kimligi=ayar.r2_hesap_kimligi,
                erisim_anahtari=ayar.r2_erisim_anahtari,
                gizli_anahtar=ayar.r2_gizli_anahtar,
                kova=ayar.r2_kova,
                zaman_asimi_sn=ayar.depo_zaman_asimi_sn,
            )
        # Eksik ayarla açılış durmaz (İ9): yükleme 503, geri kalan her şey çalışır.
        logger.warning("DEPO_SAGLAYICI=r2 ama R2_* alanlari eksik; dosya yukleme kapali")
        return KapaliDepo()
    if ayar.depo_saglayici == "yerel":
        # İndirme token'ı oturum JWT'sinden ayrı bir anahtarla imzalanır.
        imza = hashlib.sha256(f"dosya:{ayar.jwt_gizli_anahtar}".encode()).hexdigest()
        return YerelDepo(Path(ayar.depo_klasoru).resolve(), imza, ayar.api_adresi)
    return KapaliDepo()


@lru_cache
def virus_tarayici() -> VirusTarayici:
    ayar = get_settings()
    if ayar.virus_tarayici == "clamav":
        return ClamavTarayici(ayar.clamav_sunucu, ayar.clamav_port, ayar.virus_zaman_asimi_sn)
    return KapaliTarayici()


@lru_cache
def yedek_okuyucu() -> YedekOkuyucu:
    ayar = get_settings()
    if ayar.yedek_okuyucu == "playwright" and ayar.yedek_okuyucu_adresi:
        return PlaywrightYedekOkuyucu(
            ayar.yedek_okuyucu_adresi,
            ayar.yedek_okuyucu_anahtari,
            ayar.yedek_okuyucu_zaman_asimi_sn,
        )
    return KapaliYedekOkuyucu()


def servis_kipleri() -> dict[str, str]:
    """Servis adı → o an kullanılan kip (sağlık ucu için)."""
    return {
        "eposta": eposta_gonderici().kip,
        "oauth": ", ".join(sorted(oauth_saglayicilari())) or "kapali",
        "depo": depo().kip,
        "virus": virus_tarayici().kip,
        "yedek_okuyucu": yedek_okuyucu().kip,
    }
