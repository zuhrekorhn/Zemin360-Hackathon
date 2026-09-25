"""Şifre hash'i ve JWT (docs/faz-b-kimlik-ve-dongu.md § 1).

- Şifre: argon2id (`argon2-cffi` varsayılan parametreleri). bcrypt'in 72
  baytlık sessiz kesme sınırı yok.
- Token: HS256 JWT, `JWT_GIZLI_ANAHTAR` ile imzalı, 7 gün ömürlü.
  Claim'ler: `sub` (hesap id), `rol`, `iat`, `exp`. Refresh token yok; çıkış
  istemci tarafında token silinerek yapılır.

Veritabanına dokunmaz — saf fonksiyonlar, ağsız test edilir. Hesabı istekten
bulan FastAPI bağımlılığı app/api/kimlik.py'de.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings

TOKEN_OMRU = dt.timedelta(days=7)
ALGORITMA = "HS256"
SIFRE_EN_AZ = 8

_hasher = PasswordHasher()
# Olmayan bir e-postayla girişte de aynı sürede yanıt verebilmek için karşılaştırılan
# sahte hash. Aksi halde yanıt süresinden "bu e-posta kayıtlı mı" anlaşılabilirdi.
_SAHTE_HASH = _hasher.hash("zemin360-olmayan-hesap")


class TokenGecersiz(Exception):
    """Token imzası bozuk, süresi dolmuş ya da içeriği eksik."""


@dataclass(frozen=True)
class TokenIcerigi:
    hesap_id: uuid.UUID
    rol: str


def sifre_hashle(sifre: str) -> str:
    return _hasher.hash(sifre)


def sifre_dogru_mu(sifre_hash: str | None, sifre: str) -> bool:
    """Şifre hash'le uyuşuyor mu? Hash yoksa (hesap yoksa) da aynı işi yapar."""
    try:
        return _hasher.verify(sifre_hash or _SAHTE_HASH, sifre) and sifre_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def token_uret(hesap_id: uuid.UUID, rol: str, simdi: dt.datetime | None = None) -> str:
    an = simdi or dt.datetime.now(dt.UTC)
    icerik = {"sub": str(hesap_id), "rol": rol, "iat": an, "exp": an + TOKEN_OMRU}
    return jwt.encode(icerik, get_settings().jwt_gizli_anahtar, algorithm=ALGORITMA)


def token_coz(token: str) -> TokenIcerigi:
    """Token'ı doğrular ve içeriğini döner; her kusurda `TokenGecersiz`."""
    try:
        icerik = jwt.decode(
            token,
            get_settings().jwt_gizli_anahtar,
            algorithms=[ALGORITMA],
            options={"require": ["sub", "rol", "exp", "iat"]},
        )
        return TokenIcerigi(hesap_id=uuid.UUID(icerik["sub"]), rol=str(icerik["rol"]))
    except (jwt.PyJWTError, ValueError, KeyError) as hata:
        raise TokenGecersiz(str(hata)) from hata
