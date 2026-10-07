"""İş birliklerim (docs/kimlik-ve-dongu.md § 3, § 5).

İş birliği gencin kabulüyle açılır; bu liste iki tarafa da aynı görünümü
verir, e-postalar dahil (kabul edilmiş eşleşme, iletişim açık). Plan ve
adımlar Takip'in işi (docs/takip.md).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.kimlik import rol_gerekli
from app.api.takip import ilerleme_hesapla
from app.db.session import get_session
from app.models.eslesme import Eslesme
from app.models.firma_karti import FirmaKarti
from app.models.hesap import ROL_GENC, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.isbirligi import Isbirligi
from app.models.yetenek_karti import YetenekKarti
from app.schemas.eslestirme import IsbirligiOzeti
from app.servisler.eslestirme import iletisim
from app.servisler.sahiplik import (
    TARAF_ADAY,
    calisma_basligi,
    eslesmedeki_taraf,
    kullanici_id,
    kurum_id,
    taraf_adi,
)

router = APIRouter(tags=["isbirlikleri"])


def _taraf_kosulu(hesap: Hesap):
    """Profili olmayan tarafın koşulu hiç eklenmez (`= NULL` yazmayalım)."""
    kosullar = []
    if (gencin := kullanici_id(hesap)) is not None:
        kosullar.append(YetenekKarti.kullanici_id == gencin)
    if (kurumun := kurum_id(hesap)) is not None:
        # Firma iki tarafta da olabilir: ilanın sahibi ya da ortak (aday) firma.
        kosullar.append(IhtiyacKarti.kurum_id == kurumun)
        kosullar.append(FirmaKarti.kurum_id == kurumun)
    return or_(false(), *kosullar)


@router.get("/isbirliklerim", response_model=list[IsbirligiOzeti])
async def isbirliklerim(
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC, ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> list[IsbirligiOzeti]:
    """Hesabın taraf olduğu iş birlikleri; eşleşmede en son hareket olan önce.

    Başlangıç tarihi yalnızca gün tuttuğu için aynı gün açılanları sıralayamıyordu.
    """
    isbirlikleri = await oturum.scalars(
        select(Isbirligi)
        .join(Eslesme, Isbirligi.eslesme_id == Eslesme.id)
        # Aday yetenek kartı ya da firma kartı: ikisi de dış birleşim.
        .outerjoin(YetenekKarti, Eslesme.yetenek_karti_id == YetenekKarti.id)
        .outerjoin(FirmaKarti, Eslesme.firma_karti_id == FirmaKarti.id)
        .join(IhtiyacKarti, Eslesme.ihtiyac_karti_id == IhtiyacKarti.id)
        .options(
            selectinload(Isbirligi.eslesme)
            .selectinload(Eslesme.yetenek_karti)
            .selectinload(YetenekKarti.kullanici),
            selectinload(Isbirligi.eslesme)
            .selectinload(Eslesme.yetenek_karti)
            .selectinload(YetenekKarti.somut_ciktilar),
            selectinload(Isbirligi.eslesme)
            .selectinload(Eslesme.firma_karti)
            .selectinload(FirmaKarti.kurum),
            selectinload(Isbirligi.eslesme)
            .selectinload(Eslesme.ihtiyac_karti)
            .selectinload(IhtiyacKarti.kurum),
            selectinload(Isbirligi.milestonelar),
        )
        .where(_taraf_kosulu(hesap))
        .order_by(Eslesme.son_aktivite_tarihi.desc())
    )
    ozetler = []
    for isbirligi in isbirlikleri.all():
        eslesme = isbirligi.eslesme
        acik = iletisim(eslesme, hesap)
        if acik is None:
            # Gencin kabulü olmadan açılmış eski iş birliği:
            # durum `kabul_edildi` değilse e-postalar açılmaz, satır gösterilmez.
            continue
        ozetler.append(
            IsbirligiOzeti(
                isbirligi_id=isbirligi.id,
                durum=isbirligi.durum,
                baslangic_tarihi=isbirligi.baslangic_tarihi,
                eslesme_id=eslesme.id,
                aday_turu="firma" if eslesme.firma_karti_id else "genc",
                aday_adi=taraf_adi(eslesme, TARAF_ADAY),
                genc_adi=eslesme.yetenek_karti.kullanici.ad if eslesme.yetenek_karti else None,
                kurum_adi=eslesme.ihtiyac_karti.kurum.ad,
                rol_alani=eslesme.yetenek_karti.rol_alani if eslesme.yetenek_karti else None,
                tarafim=eslesmedeki_taraf(hesap, eslesme),
                problem_tanimi=eslesme.ihtiyac_karti.problem_tanimi,
                basari_kriteri=eslesme.ihtiyac_karti.basari_kriteri,
                calisma_basligi=calisma_basligi(eslesme),
                iletisim=acik,
                ilerleme=ilerleme_hesapla(isbirligi.milestonelar),
            )
        )
    return ozetler
