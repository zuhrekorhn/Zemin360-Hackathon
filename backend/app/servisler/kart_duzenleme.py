"""Kart ve iş kalemi düzenlemesinin uygulanması (docs/agent-specs.md § 1).

Kural app/agents/kart_duzenleme.py'de; burada modele yazılması. Commit ve arka
plan işi (kart hazırlama) uçların işi: değişiklik ve yan etkileri aynı işlemde.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.eslestirme import DURUM_ONERILDI
from app.agents.kart_duzenleme import (
    IS_KALEMI_ALANLARI,
    KART_ALANLARI,
    degisen_alanlar,
    dogrulama_sifirlanmali_mi,
)
from app.agents.kesif import potansiyel_kurali
from app.core.is_kalemi import kanit_bekliyor
from app.models.eslesme import Eslesme
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler.dogrulama.parcalar import link_parcasi_ekle


def _yaz(nesne: Any, degerler: dict[str, Any], izinli: tuple[str, ...]) -> set[str]:
    """İzinli alanlardan değişenleri yazar; boş metin None olur. Döner: değişenler."""
    mevcut = {alan: getattr(nesne, alan) for alan in izinli}
    temiz = {
        alan: (deger.strip() or None) if isinstance(deger, str) else deger
        for alan, deger in degerler.items()
        if alan in izinli
    }
    degisenler = degisen_alanlar(mevcut, temiz)
    for alan in degisenler:
        setattr(nesne, alan, list(temiz[alan]) if isinstance(temiz[alan], list) else temiz[alan])
    return degisenler


def karti_guncelle(kart: YetenekKarti, degerler: dict[str, Any]) -> set[str]:
    return _yaz(kart, degerler, KART_ALANLARI)


def is_kalemini_guncelle(cikti: SomutCikti, degerler: dict[str, Any]) -> set[str]:
    """Değişenleri yazar. İddia değiştiyse güven göstergesi sıfırlanır.

    Sıfırlama: gösterge silinir, `icerik_tarihi` şimdi olur. Bu andan önce
    verilmiş referans yanıtları silinmez, geçmiş olarak kalır ama puana girmez.
    Kanıt linki varsa kart hazırlama kalemi yeniden puanlar. Kanıtın kendisi
    burada değişmez (Doğrulama'nın kanıt bölümü).
    """
    degisenler = _yaz(cikti, degerler, IS_KALEMI_ALANLARI)
    if dogrulama_sifirlanmali_mi(degisenler):
        cikti.guven_skoru = None
        cikti.icerik_tarihi = dt.datetime.now(dt.UTC)
    return degisenler


def is_kalemi_ekle(
    kart: YetenekKarti, degerler: dict[str, Any], kanit_linki: str | None = None
) -> SomutCikti:
    """Yeni iş kalemi; formda link verildiyse ilk kanıt parçası olur (tek kapıdan).

    Değerlendirme yanıttan sonra kart hazırlamada yapılır.
    """
    cikti = SomutCikti(
        **{alan: degerler.get(alan) for alan in IS_KALEMI_ALANLARI},
        kanit_parcalari=[],
        referans_istekleri=[],
    )
    if kanit_linki and kanit_linki.strip():
        link_parcasi_ekle(cikti, kanit_linki)
    kart.somut_ciktilar.append(cikti)
    return cikti


def is_kalemini_sil(kart: YetenekKarti, cikti: SomutCikti) -> None:
    kart.somut_ciktilar.remove(cikti)


async def kart_degisti(oturum: AsyncSession, kart: YetenekKarti) -> int:
    """Her kart değişikliğinin ortak kısmı. Döner: yeni versiyon.

    - Versiyon artar (kart hazırlamanın idempotentlik anahtarı).
    - `kanit_bekleyen` ve "potansiyel" kuralı iş kalemleriyle tutarlı kalır.
    - Bu kartın yalnızca `onerildi` önerilerinin gerekçesi ve uygunluk kararı
      boşaltılır (karar gerekçeye dayanır); pipeline ikisini yeniden yazar. Gizli
      (`uygun_degil`) kayıt da yeniden yargılanır. Karar verilmiş kayıtlara (genç ilgi
      gösterdi, kurum ilgilendi, kabul, red) dokunulmaz (docs/kararlar.md G14).
    """
    kart.versiyon += 1
    # Bayrağın hesabı için kalemlerin parçaları ve referans istekleri yüklü olmalı.
    kart.kanit_bekleyen = kanit_bekliyor(kart.somut_ciktilar)
    kart.deneyim_seviyesi = potansiyel_kurali(kart.deneyim_seviyesi, len(kart.somut_ciktilar))
    await oturum.execute(
        update(Eslesme)
        .where(Eslesme.yetenek_karti_id == kart.id, Eslesme.durum == DURUM_ONERILDI)
        .values(gerekce_metni=None, uygunluk=None)
    )
    return kart.versiyon


async def gosterge_degisti(oturum: AsyncSession, kart_id: uuid.UUID) -> int:
    """Bir kalemin güven göstergesi değişti (kanıt, değerlendirme, itiraz, referans yanıtı).

    Kart değişikliğinin ortak kısmı uygulanır: sürüm artar, `kanit_bekleyen`
    tazelenir, `onerildi` önerilerin gerekçesi boşalır. Çağıran uç commit'ten
    sonra kart hazırlamayı (yeniden eşleştirme) arka plana alır: uyum skoru
    doğrulama bonusunu içerir, gösterge değişince eşleşmeler de tazelenmeli.
    Döner: yeni sürüm.
    """
    kart = await oturum.scalar(
        select(YetenekKarti)
        .options(
            selectinload(YetenekKarti.somut_ciktilar).selectinload(SomutCikti.referans_istekleri),
            selectinload(YetenekKarti.somut_ciktilar).selectinload(SomutCikti.kanit_parcalari),
        )
        .where(YetenekKarti.id == kart_id)
        .with_for_update(of=YetenekKarti)
    )
    if kart is None:
        raise LookupError(kart_id)
    return await kart_degisti(oturum, kart)
