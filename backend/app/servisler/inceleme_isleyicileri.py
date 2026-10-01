"""İşaret türü → kararın etkisi (Strategy; docs/plans/dogrulama-iyilestirme.md § 9).

Kalem işaretleri (itiraz sınırı, ileride kanıt işaretleri) aynı işleyiciyi
kullanır: karar puanı değiştirmez, gence sonucu bildirir. Etkisi farklı olan
tür (ad değişikliği gibi) kendi işleyicisini bu tabloya ekler.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.inceleme_durumu import KAPANDI
from app.models.bildirim import TUR_INCELEME_SONUCU
from app.models.inceleme_isareti import IncelemeIsareti
from app.models.somut_cikti import SomutCikti
from app.servisler.inceleme import KararEtkisi, KararIsleyici


def _not_eki(isaret: IncelemeIsareti) -> str:
    return f" GİRVAK'ın notu: {isaret.girvak_notu}" if isaret.girvak_notu else ""


class KalemIsleyici:
    """Kalemle ilgili işaret. "Doğrulanamadı" kalemin puanını değiştirmez (İ1);
    genç yeni kanıt ekleyerek yeniden değerlendirme isteyebilir."""

    async def uygula(
        self, oturum: AsyncSession, isaret: IncelemeIsareti, karar: str
    ) -> KararEtkisi:
        cikti = (
            await oturum.get(SomutCikti, isaret.somut_cikti_id) if isaret.somut_cikti_id else None
        )
        ad = f"“{cikti.baslik}” çalışmanı" if cikti else "çalışmanı"
        if karar == KAPANDI:
            metin = f"GİRVAK {ad} inceledi ve bir sorun görmedi."
        else:
            metin = (
                f"GİRVAK {ad} inceledi ve şimdilik doğrulayamadı. Yeni bir kanıt "
                "eklersen çalışman yeniden değerlendirilir."
            )
        return KararEtkisi(
            bildirim_turu=TUR_INCELEME_SONUCU, bildirim_metni=metin + _not_eki(isaret)
        )


ISLEYICILER: dict[str, KararIsleyici] = {}
VARSAYILAN = KalemIsleyici()


def isleyici(tur: str) -> KararIsleyici:
    return ISLEYICILER.get(tur, VARSAYILAN)
