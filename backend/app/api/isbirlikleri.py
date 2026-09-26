"""İş birliklerim (docs/faz-b-kimlik-ve-dongu.md § 3, § 5).

İş birliği gencin kabulüyle açılır; bu liste iki tarafa da aynı görünümü
verir, e-postalar dahil (kabul edilmiş eşleşme, iletişim açık). Milestone
ve zaman çizelgesi Takip Ajanı'nın işi (Faz D).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.eslestirme import iletisim
from app.api.kimlik import rol_gerekli
from app.api.sahiplik import kullanici_id, kurum_id
from app.db.session import get_session
from app.models.eslesme import Eslesme
from app.models.hesap import ROL_GENC, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.isbirligi import Isbirligi
from app.models.yetenek_karti import YetenekKarti
from app.schemas.eslestirme import IsbirligiOzeti

router = APIRouter(tags=["isbirlikleri"])


def _taraf_kosulu(hesap: Hesap):
    """Profili olmayan tarafın koşulu hiç eklenmez (`= NULL` yazmayalım)."""
    kosullar = []
    if (gencin := kullanici_id(hesap)) is not None:
        kosullar.append(YetenekKarti.kullanici_id == gencin)
    if (kurumun := kurum_id(hesap)) is not None:
        kosullar.append(IhtiyacKarti.kurum_id == kurumun)
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
        .join(YetenekKarti, Eslesme.yetenek_karti_id == YetenekKarti.id)
        .join(IhtiyacKarti, Eslesme.ihtiyac_karti_id == IhtiyacKarti.id)
        .options(
            selectinload(Isbirligi.eslesme)
            .selectinload(Eslesme.yetenek_karti)
            .selectinload(YetenekKarti.kullanici),
            selectinload(Isbirligi.eslesme)
            .selectinload(Eslesme.ihtiyac_karti)
            .selectinload(IhtiyacKarti.kurum),
        )
        .where(_taraf_kosulu(hesap))
        .order_by(Eslesme.son_aktivite_tarihi.desc())
    )
    ozetler = []
    for isbirligi in isbirlikleri.all():
        eslesme = isbirligi.eslesme
        acik = iletisim(eslesme, hesap)
        if acik is None:
            # Faz B öncesi akışta gencin kabulü olmadan açılmış iş birliği:
            # durum `kabul_edildi` değilse e-postalar açılmaz, satır gösterilmez.
            continue
        ozetler.append(
            IsbirligiOzeti(
                isbirligi_id=isbirligi.id,
                durum=isbirligi.durum,
                baslangic_tarihi=isbirligi.baslangic_tarihi,
                eslesme_id=eslesme.id,
                genc_adi=eslesme.yetenek_karti.kullanici.ad,
                kurum_adi=eslesme.ihtiyac_karti.kurum.ad,
                rol_alani=eslesme.yetenek_karti.rol_alani,
                problem_tanimi=eslesme.ihtiyac_karti.problem_tanimi,
                iletisim=acik,
            )
        )
    return ozetler
