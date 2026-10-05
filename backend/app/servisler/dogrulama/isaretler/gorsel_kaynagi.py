"""Görsel başka bir sayfada (plan § 4.3, § 9): `gorsel_baskasinda`.

Yükleme anında, görsel parça eklendikten sonra çağrılır. Kaynak araması
(`GorselArayici`, Cloud Vision) yalnızca: servis açıksa, genç tasarım /
fotoğraf alanındaysa ve aylık tavan dolmadıysa. Birebir eşin bulunduğu,
gencin kendi hesabında olmayan sayfalar işarettir; puan değişmez (İ1).
Arama sonucu parçanın `belge["kaynak_aramasi"]`'na yazılır (GİRVAK için).
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dogrulama.gorsel_kaynagi import baskasindaki_sayfalar, gorsel_alani_mi
from app.core.config import get_settings
from app.core.dis_servisler import kurulum
from app.core.kanit_okuma.adres import normal_url
from app.core.kanit_okuma.belge import ParcaTuru
from app.models.inceleme_isareti import TUR_GORSEL_BASKASINDA
from app.models.kanit_parcasi import KanitParcasi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler import inceleme, servis_kullanimi
from app.servisler.dogrulama.sorgular import bagli_hesap_bilgileri

logger = logging.getLogger("zemin360.gorsel_kaynagi")

SERVIS = "gorsel_arayici"


async def _kendi_adresleri(oturum: AsyncSession, kart_id: uuid.UUID) -> list[str]:
    """Gencin kartındaki bütün kanıt linkleri (kendi portfolyo hesapları)."""
    return list(
        await oturum.scalars(
            select(KanitParcasi.url)
            .join(SomutCikti, SomutCikti.id == KanitParcasi.somut_cikti_id)
            .where(SomutCikti.yetenek_karti_id == kart_id, KanitParcasi.url.is_not(None))
        )
    )


async def kaynak_ara(
    oturum: AsyncSession,
    parca: KanitParcasi,
    cikti: SomutCikti,
    kullanici_id: uuid.UUID,
    veri: bytes,
) -> None:
    arayici = kurulum.gorsel_arayici()
    if arayici.kip == "kapali" or parca.tur != ParcaTuru.GORSEL.value:
        return
    kart = await oturum.get(YetenekKarti, cikti.yetenek_karti_id)
    if kart is None or not gorsel_alani_mi(kart.rol_alani, kart.araclar_teknolojiler or ()):
        return
    if not await servis_kullanimi.hak_al(oturum, SERVIS, get_settings().gorsel_arama_aylik_tavan):
        logger.info("gorsel arama aylik tavani doldu; arama yapilmadi")
        return
    sonuc = await arayici.ara(veri)
    if sonuc is None:
        return
    baskasinda = baskasindaki_sayfalar(
        sonuc.sayfalar,
        await bagli_hesap_bilgileri(oturum, kullanici_id),
        await _kendi_adresleri(oturum, kart.id),
    )
    parca.belge = {
        **(parca.belge or {}),
        "kaynak_aramasi": {
            "tarih": dt.datetime.now(dt.UTC).isoformat(),
            "tam_eslesen_sayfa": sum(1 for s in sonuc.sayfalar if s.tam_eslesme),
            "baskasinda": [{"adres": s.adres, "baslik": s.baslik} for s in baskasinda],
        },
    }
    if not baskasinda:
        return
    await oturum.flush()  # parçanın kimliği sinyale yazılır
    await inceleme.sinyal_ekle(
        oturum,
        TUR_GORSEL_BASKASINDA,
        kullanici_id,
        cikti.id,
        "sayfalar",
        [
            {
                "anahtar": f"{parca.id}:{normal_url(s.adres)}",
                "parca_id": str(parca.id),
                "dosya_adi": parca.dosya_adi,
                "adres": s.adres,
                "baslik": s.baslik,
            }
            for s in baskasinda
        ],
    )
