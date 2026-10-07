"""Aynı kanıt başka bir hesapta (docs/dogrulama.md § 9): `ayni_iddia_cok_hesapta`.

Üç yoldan aranır, hepsi başka bir gencin kanıt parçalarında:
  - link: aynı normalleştirilmiş adres (`normal_url`, indeksli);
  - dosya: aynı içerik özeti (ham dosyanın SHA-256'sı, indeksli);
  - görsel: benzer algısal özet (pHash, bit farkı `BENZERLIK_ESIGI`'ne kadar;
    Postgres `bit_count`, küçük ölçekte tam tarama).
Takım projesi: iki parçanın da sahipliği bağlı hesabın katkıcı listesiyle
(OAuth) doğrulandıysa ikisi de o işte vardır, eşleşme işaret değildir.

İşaret puanı değiştirmez (İ1). Değerlendirmeden sonra çağrılır (sahiplik
okunmuş olsun); aynı eşleşme bir kez kuyruğa düşer (`inceleme.sinyal_ekle`).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Integer, cast, func, literal, select
from sqlalchemy.dialects.postgresql import BIT
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gorsel_ozeti import BENZERLIK_ESIGI
from app.core.kanit_okuma.belge import ParcaTuru, SahiplikKaynagi
from app.models.inceleme_isareti import TUR_AYNI_IDDIA_COK_HESAPTA
from app.models.kanit_parcasi import KanitParcasi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler import inceleme

# Parça başına en çok bu kadar eşleşme yazılır (kuyruk satırı okunur kalsın).
PARCA_BASINA_ESLESME = 5

NEDEN_ADRES = "adres"
NEDEN_DOSYA = "dosya"
NEDEN_GORSEL = "gorsel"


def _bit64(sutun):
    return cast(literal("x").op("||")(sutun), BIT(64))


def _baskalarinin_parcalari(kullanici_id: uuid.UUID):
    return (
        select(
            KanitParcasi.id,
            KanitParcasi.sahiplik_kaynagi,
            YetenekKarti.kullanici_id,
            YetenekKarti.id,
        )
        .join(SomutCikti, SomutCikti.id == KanitParcasi.somut_cikti_id)
        .join(YetenekKarti, YetenekKarti.id == SomutCikti.yetenek_karti_id)
        .where(YetenekKarti.kullanici_id != kullanici_id)
        .limit(PARCA_BASINA_ESLESME)
    )


def takim_projesi_mi(benim: str | None, onun: str | None) -> bool:
    """İki parça da katkıcı listesiyle doğrulandı: aynı işte birlikte çalıştılar."""
    oauth = SahiplikKaynagi.OAUTH.value
    return benim == oauth and onun == oauth


async def _eslesenler(
    oturum: AsyncSession, parca: KanitParcasi, kullanici_id: uuid.UUID
) -> list[tuple[str, Any, Any, Any, Any]]:
    """(neden, diğer parça, diğer sahiplik, diğer kullanıcı, diğer kart)."""
    sorgu = _baskalarinin_parcalari(kullanici_id)
    sonuc: list[tuple[str, Any, Any, Any, Any]] = []
    if parca.tur == ParcaTuru.LINK.value and parca.normal_url:
        satirlar = await oturum.execute(sorgu.where(KanitParcasi.normal_url == parca.normal_url))
        sonuc += [(NEDEN_ADRES, *s) for s in satirlar.all()]
    if parca.dosya_ozeti:
        satirlar = await oturum.execute(sorgu.where(KanitParcasi.dosya_ozeti == parca.dosya_ozeti))
        sonuc += [(NEDEN_DOSYA, *s) for s in satirlar.all()]
    if parca.phash:
        fark = func.bit_count(_bit64(KanitParcasi.phash).op("#")(_bit64(literal(parca.phash))))
        satirlar = await oturum.execute(
            sorgu.where(
                KanitParcasi.phash.is_not(None),
                KanitParcasi.dosya_ozeti.is_distinct_from(parca.dosya_ozeti),
                cast(fark, Integer) <= BENZERLIK_ESIGI,
            )
        )
        sonuc += [(NEDEN_GORSEL, *s) for s in satirlar.all()]
    return sonuc


async def tekrar_eden_kanit(
    oturum: AsyncSession, cikti: SomutCikti, kullanici_id: uuid.UUID
) -> None:
    """Kalemin parçalarını başka hesaplarda arar; yeni eşleşme varsa işaret açar."""
    sinyaller: list[dict[str, Any]] = []
    for parca in cikti.kanit_parcalari:
        for neden, diger_id, diger_sahiplik, diger_kullanici, diger_kart in await _eslesenler(
            oturum, parca, kullanici_id
        ):
            if neden == NEDEN_ADRES and takim_projesi_mi(parca.sahiplik_kaynagi, diger_sahiplik):
                continue
            sinyaller.append(
                {
                    "anahtar": f"{parca.id}:{diger_id}",
                    "neden": neden,
                    "parca_id": str(parca.id),
                    "adres": parca.url,
                    "dosya_adi": parca.dosya_adi,
                    "diger_parca_id": str(diger_id),
                    "diger_kullanici_id": str(diger_kullanici),
                    "diger_kart_id": str(diger_kart),
                }
            )
    if sinyaller:
        await inceleme.sinyal_ekle(
            oturum, TUR_AYNI_IDDIA_COK_HESAPTA, kullanici_id, cikti.id, "eslesmeler", sinyaller
        )
