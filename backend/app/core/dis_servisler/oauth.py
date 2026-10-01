"""Hesap bağlama için OAuth sağlayıcıları (Strategy + Adapter; plan § 6.1, § 14.3).

Her sağlayıcı iki şey yapar: kullanıcıyı yönlendireceğimiz yetki adresini kurar
ve dönen kodla hesabın kimliğini okur. Token yalnızca kimliği okumak için
kullanılır, saklanmaz ve log'a yazılmaz (§ 6.1). Yeni sağlayıcı = yeni sınıf +
`kurulum.oauth_saglayicilari`'na bir satır; servis değişmez.

İstekler sağlayıcının sabit adreslerine gider (kullanıcı adresi değil), bu yüzden
güvenli istek katmanından değil, diğer dış servis adaptörleri gibi doğrudan
httpx ile; her çağrı zaman aşımlı ve gözlemli.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx

from app.core.dis_servisler.sarmalayicilar import gozlemli, zaman_asimli


@dataclass(frozen=True)
class DisHesap:
    """Bağlanan hesabın kimliği: görünen ad ve değişmeyen kimlik."""

    kullanici_adi: str
    dis_kimlik: str


class OAuthReddedildi(Exception):
    """Sağlayıcı kodu kabul etmedi (süresi dolmuş, kullanılmış ya da sahte kod)."""


class OAuthSaglayici(Protocol):
    saglayici: str

    def yetki_adresi(self, durum: str, donus_adresi: str) -> str: ...

    async def hesabi_oku(self, kod: str, donus_adresi: str) -> DisHesap: ...


@dataclass(frozen=True)
class OAuthAyari:
    istemci: str
    gizli: str
    zaman_asimi_sn: float
    tasima: httpx.AsyncBaseTransport | None = None


class _OAuthIstemcisi:
    """Yetkilendirme kodu akışının ortak kısmı: yetki adresi ve kod → token takası.

    Alt sınıf adresleri, kapsamı ve token yanıtından kimliğin okunuşunu verir.
    """

    saglayici: str
    YETKI_ADRESI: str
    TOKEN_ADRESI: str
    KAPSAM: str

    def __init__(self, ayar: OAuthAyari) -> None:
        self._ayar = ayar
        self.hesabi_oku = gozlemli(f"oauth_{self.saglayici}")(
            zaman_asimli(ayar.zaman_asimi_sn)(self._hesabi_oku)
        )

    def yetki_adresi(self, durum: str, donus_adresi: str) -> str:
        sorgu = {
            "client_id": self._ayar.istemci,
            "redirect_uri": donus_adresi,
            "scope": self.KAPSAM,
            "state": durum,
            "response_type": "code",
        }
        return f"{self.YETKI_ADRESI}?{urlencode(sorgu)}"

    async def _hesabi_oku(self, kod: str, donus_adresi: str) -> DisHesap:
        async with httpx.AsyncClient(transport=self._ayar.tasima) as istemci:
            yanit = await istemci.post(
                self.TOKEN_ADRESI,
                data={
                    "client_id": self._ayar.istemci,
                    "client_secret": self._ayar.gizli,
                    "code": kod,
                    "redirect_uri": donus_adresi,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            if yanit.status_code in (400, 401):
                raise OAuthReddedildi(self.saglayici)
            yanit.raise_for_status()
            govde = yanit.json()
            # GitHub geçersiz kodda 200 ve "error" döner.
            if "error" in govde or "access_token" not in govde:
                raise OAuthReddedildi(self.saglayici)
            return await self._kimlik(istemci, govde)

    async def _kimlik(self, istemci: httpx.AsyncClient, token_yaniti: dict[str, Any]) -> DisHesap:
        raise NotImplementedError


async def _kullanici_getir(istemci: httpx.AsyncClient, adres: str, token: str) -> dict[str, Any]:
    yanit = await istemci.get(
        adres, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
    )
    yanit.raise_for_status()
    return yanit.json()


class GithubOAuth(_OAuthIstemcisi):
    saglayici = "github"
    YETKI_ADRESI = "https://github.com/login/oauth/authorize"
    TOKEN_ADRESI = "https://github.com/login/oauth/access_token"
    KAPSAM = "read:user"

    async def _kimlik(self, istemci: httpx.AsyncClient, token_yaniti: dict[str, Any]) -> DisHesap:
        kullanici = await _kullanici_getir(
            istemci, "https://api.github.com/user", token_yaniti["access_token"]
        )
        return DisHesap(kullanici_adi=kullanici["login"], dis_kimlik=str(kullanici["id"]))


class GitlabOAuth(_OAuthIstemcisi):
    saglayici = "gitlab"
    YETKI_ADRESI = "https://gitlab.com/oauth/authorize"
    TOKEN_ADRESI = "https://gitlab.com/oauth/token"
    KAPSAM = "read_user"

    async def _kimlik(self, istemci: httpx.AsyncClient, token_yaniti: dict[str, Any]) -> DisHesap:
        kullanici = await _kullanici_getir(
            istemci, "https://gitlab.com/api/v4/user", token_yaniti["access_token"]
        )
        return DisHesap(kullanici_adi=kullanici["username"], dis_kimlik=str(kullanici["id"]))


class OrcidOAuth(_OAuthIstemcisi):
    """ORCID token yanıtı iD'yi zaten taşır; ayrıca kullanıcı isteği gerekmez.

    Bağlı ORCID iD'nin puana etkisi akademik okuyucuyla gelir (yazar listesinde
    iD; plan § 8); bugün bağlantı saklanır.
    """

    saglayici = "orcid"
    YETKI_ADRESI = "https://orcid.org/oauth/authorize"
    TOKEN_ADRESI = "https://orcid.org/oauth/token"
    KAPSAM = "/authenticate"

    async def _kimlik(self, istemci: httpx.AsyncClient, token_yaniti: dict[str, Any]) -> DisHesap:
        orcid = token_yaniti.get("orcid")
        if not orcid:
            raise OAuthReddedildi(self.saglayici)
        return DisHesap(kullanici_adi=orcid, dis_kimlik=orcid)
