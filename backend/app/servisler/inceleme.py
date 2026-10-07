"""GİRVAK inceleme kuyruğu: işaret açma ve karar (docs/dogrulama.md § 9).

İşaret puanı kendiliğinden değiştirmez (İ1). Akış iki parçalı:
  - `isaret_ac`: sinyali gören servis çağırır. Aynı konu için açık işaret
    varsa yenisi açılmaz, ayrıntısı açık olana eklenir (tek açık işaret).
  - `karar_ver`: GİRVAK karar verir. Geçiş kuralı `agents/inceleme_durumu.py`'de;
    türe özel etki (ad değişikliğini uygulamak gibi) ve gence giden bildirim
    `KararIsleyici`'dedir (Strategy). Yeni tür = yeni işleyici + tabloya bir
    satır (`inceleme_isleyicileri.py`); bu dosya değişmez.

Sözleşme (diğer servislerle aynı): model değişir, commit, arka plan işi ve
HTTP'ye çeviri çağıranın işidir. Bildirim kararla aynı işlemde yazılır.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.inceleme_durumu import ACIK, gecerli_dogrulanamadilar, inceleme_gecisi
from app.models.inceleme_isareti import KALEM_KARARI_TURLERI, IncelemeIsareti
from app.models.kullanici import Kullanici
from app.servisler.bildirim import bildirim_ekle


@dataclass(frozen=True)
class ArkaPlanIsi:
    """Karardan sonra yanıttan sonra çalışacak iş (uç `BackgroundTasks`'a ekler)."""

    fonksiyon: Callable[..., Awaitable[None]]
    argumanlar: tuple[Any, ...] = ()


@dataclass(frozen=True)
class KararEtkisi:
    bildirim_turu: str
    # Gence giden metin ("sen"); e-posta içermez.
    bildirim_metni: str
    arka_plan: Sequence[ArkaPlanIsi] = field(default_factory=tuple)


class KararIsleyici(Protocol):
    async def uygula(
        self, oturum: AsyncSession, isaret: IncelemeIsareti, karar: str
    ) -> KararEtkisi: ...


async def acik_isaret(
    oturum: AsyncSession,
    tur: str,
    kullanici_id: uuid.UUID,
    somut_cikti_id: uuid.UUID | None = None,
) -> IncelemeIsareti | None:
    return await oturum.scalar(
        select(IncelemeIsareti)
        .where(
            IncelemeIsareti.tur == tur,
            IncelemeIsareti.kullanici_id == kullanici_id,
            IncelemeIsareti.somut_cikti_id.is_(None)
            if somut_cikti_id is None
            else IncelemeIsareti.somut_cikti_id == somut_cikti_id,
            IncelemeIsareti.durum == ACIK,
        )
        .with_for_update()
    )


async def isaret_ac(
    oturum: AsyncSession,
    tur: str,
    kullanici_id: uuid.UUID,
    *,
    somut_cikti_id: uuid.UUID | None = None,
    ayrinti: dict[str, Any] | None = None,
    birlestir: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
) -> tuple[IncelemeIsareti, bool]:
    """Açık işareti döner (yeni mi?). Açık işaret varsa `birlestir` ayrıntıyı
    günceller (verilmezse ayrıntı olduğu gibi kalır)."""
    mevcut = await acik_isaret(oturum, tur, kullanici_id, somut_cikti_id)
    if mevcut is not None:
        if birlestir is not None and ayrinti is not None:
            mevcut.ayrinti = birlestir(dict(mevcut.ayrinti), ayrinti)
        return mevcut, False
    isaret = IncelemeIsareti(
        tur=tur, kullanici_id=kullanici_id, somut_cikti_id=somut_cikti_id, ayrinti=ayrinti or {}
    )
    oturum.add(isaret)
    await oturum.flush()
    return isaret, True


def _sinyalleri_birlestir(alan: str) -> Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]:
    def birlestir(eski: dict[str, Any], yeni: dict[str, Any]) -> dict[str, Any]:
        return {**eski, alan: [*eski.get(alan, []), *yeni[alan]]}

    return birlestir


async def sinyal_ekle(
    oturum: AsyncSession,
    tur: str,
    kullanici_id: uuid.UUID,
    somut_cikti_id: uuid.UUID,
    alan: str,
    sinyaller: Sequence[dict[str, Any]],
) -> IncelemeIsareti | None:
    """Kanıt sinyallerini (eşleşme, çelişki…) kalemin işaretine ekler.

    Her sinyalin bir `anahtar`'ı vardır. Bu kalemde aynı türden HERHANGİ bir
    işarette (açık ya da kararlı) görülmüş anahtar yeniden eklenmez: GİRVAK'ın
    "sorun yok" dediği eşleşme her değerlendirmede kuyruğa dönmesin. Yeni
    sinyal yoksa işaret açılmaz (`None`).
    """
    onceki = await oturum.scalars(
        select(IncelemeIsareti.ayrinti).where(
            IncelemeIsareti.tur == tur,
            IncelemeIsareti.kullanici_id == kullanici_id,
            IncelemeIsareti.somut_cikti_id == somut_cikti_id,
        )
    )
    gorulen = {s.get("anahtar") for ayrinti in onceki for s in (ayrinti or {}).get(alan, [])}
    yeniler: list[dict[str, Any]] = []
    for sinyal in sinyaller:
        if sinyal["anahtar"] not in gorulen:
            gorulen.add(sinyal["anahtar"])
            yeniler.append(sinyal)
    if not yeniler:
        return None
    isaret, _ = await isaret_ac(
        oturum,
        tur,
        kullanici_id,
        somut_cikti_id=somut_cikti_id,
        ayrinti={alan: yeniler},
        birlestir=_sinyalleri_birlestir(alan),
    )
    return isaret


async def kalem_kararlari(oturum: AsyncSession, somut_cikti_id: uuid.UUID) -> list[IncelemeIsareti]:
    """Kalemin geçerli "doğrulanamadı" kararları (etiket; kural `gecerli_dogrulanamadilar`)."""
    isaretler = await oturum.scalars(
        select(IncelemeIsareti).where(
            IncelemeIsareti.somut_cikti_id == somut_cikti_id,
            IncelemeIsareti.tur.in_(KALEM_KARARI_TURLERI),
        )
    )
    return gecerli_dogrulanamadilar(isaretler)


async def itiraz_bekliyor_mu(oturum: AsyncSession, somut_cikti_id: uuid.UUID) -> bool:
    """Gencin itiraz notu taşıyan açık bir işaret var mı (hak dolan itiraz ya da
    "doğrulanamadı" kararına itiraz)? Arayüz itirazı kapatır."""
    return bool(
        await oturum.scalar(
            select(IncelemeIsareti.id)
            .where(
                IncelemeIsareti.somut_cikti_id == somut_cikti_id,
                IncelemeIsareti.durum == ACIK,
                IncelemeIsareti.ayrinti.has_key("itiraz_notlari"),
            )
            .limit(1)
        )
    )


async def karar_ver(
    oturum: AsyncSession,
    isaret: IncelemeIsareti,
    karar: str,
    girvak_notu: str | None,
    isleyici: KararIsleyici,
) -> Sequence[ArkaPlanIsi]:
    """Kararı uygular; aynı kararın tekrarı yan etkisiz (boş liste).

    Kapanmış işarete başka karar `GecersizKarar` (uçta 409). İşaret satırı
    çağıran tarafından kilitlenmiş okunmalıdır (`with_for_update`).
    """
    hedef = inceleme_gecisi(isaret.durum, karar)
    if hedef is None:
        return ()
    isaret.durum = hedef
    isaret.girvak_notu = girvak_notu
    isaret.kapanma_tarihi = dt.datetime.now(dt.UTC)
    etki = await isleyici.uygula(oturum, isaret, karar)
    kullanici = await oturum.get(Kullanici, isaret.kullanici_id)
    bildirim_ekle(oturum, kullanici.hesap_id, etki.bildirim_turu, etki.bildirim_metni)
    return etki.arka_plan
