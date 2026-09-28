"""Kart ve iş kalemi düzenlemesinin uygulanması (docs/plans/genc-akisi.md § 6).

Kural app/agents/kart_duzenleme.py'de; burada modele yazılması. Commit ve arka
plan işi (kart hazırlama) uçların işi: değişiklik ve yan etkileri aynı işlemde.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.eslestirme import DURUM_ONERILDI
from app.agents.kart_duzenleme import (
    IS_KALEMI_ALANLARI,
    KART_ALANLARI,
    degisen_alanlar,
    dogrulama_sifirlanmali_mi,
)
from app.agents.kesif import potansiyel_kurali
from app.models.eslesme import Eslesme
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti


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
    """Değişenleri yazar. İçerik ya da link değiştiyse güven göstergesi sıfırlanır.

    Sıfırlama: gösterge silinir, `icerik_tarihi` şimdi olur. Bu andan önce
    verilmiş referans yanıtları silinmez, geçmiş olarak kalır ama puana girmez.
    Kanıt linki varsa kart hazırlama kalemi yeniden puanlar.
    """
    degisenler = _yaz(cikti, degerler, IS_KALEMI_ALANLARI)
    if dogrulama_sifirlanmali_mi(degisenler):
        cikti.guven_skoru = None
        cikti.icerik_tarihi = dt.datetime.now(dt.UTC)
    return degisenler


def is_kalemi_ekle(kart: YetenekKarti, degerler: dict[str, Any]) -> SomutCikti:
    cikti = SomutCikti(**{alan: degerler.get(alan) for alan in IS_KALEMI_ALANLARI})
    kart.somut_ciktilar.append(cikti)
    return cikti


def is_kalemini_sil(kart: YetenekKarti, cikti: SomutCikti) -> None:
    kart.somut_ciktilar.remove(cikti)


async def kart_degisti(oturum: AsyncSession, kart: YetenekKarti) -> int:
    """Her kart değişikliğinin ortak kısmı. Döner: yeni versiyon.

    - Versiyon artar (kart hazırlamanın idempotentlik anahtarı).
    - `kanit_bekleyen` ve "potansiyel" kuralı iş kalemleriyle tutarlı kalır.
    - Bu kartın yalnızca `onerildi` önerilerinin gerekçesi boşaltılır; pipeline
      yenisini yazar. Karar verilmiş kayıtlara (genç ilgi gösterdi, kurum
      ilgilendi, kabul, red) dokunulmaz (plan § 0, karar 14).
    """
    kart.versiyon += 1
    kart.kanit_bekleyen = any(not c.kanit_linki for c in kart.somut_ciktilar)
    kart.deneyim_seviyesi = potansiyel_kurali(kart.deneyim_seviyesi, len(kart.somut_ciktilar))
    await oturum.execute(
        update(Eslesme)
        .where(Eslesme.yetenek_karti_id == kart.id, Eslesme.durum == DURUM_ONERILDI)
        .values(gerekce_metni=None)
    )
    return kart.versiyon
