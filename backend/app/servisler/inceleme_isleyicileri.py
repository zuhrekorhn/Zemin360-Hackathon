"""İşaret türü → kararın etkisi (Strategy; docs/dogrulama.md § 9).

Kalem işaretleri (itiraz sınırı, ileride kanıt işaretleri) aynı işleyiciyi
kullanır: karar puanı değiştirmez, gence sonucu bildirir. Etkisi farklı olan
tür (ad değişikliği gibi) kendi işleyicisini bu tabloya ekler.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.inceleme_durumu import KAPANDI
from app.models.bildirim import TUR_INCELEME_SONUCU
from app.models.inceleme_isareti import (
    TUR_AD_DEGISIKLIGI,
    TUR_EDEVLET_BARKODU,
    TUR_PROFIL_KODU_ELLE,
    IncelemeIsareti,
)
from app.models.somut_cikti import SomutCikti
from app.servisler.dogrulama.capalar.edevlet import EdevletIsleyici
from app.servisler.hesap_baglama import ProfilKoduIsleyici
from app.servisler.inceleme import KararEtkisi, KararIsleyici
from app.servisler.kimlik_dogrulama import AdDegisikligiIsleyici


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


ISLEYICILER: dict[str, KararIsleyici] = {
    TUR_AD_DEGISIKLIGI: AdDegisikligiIsleyici(),
    TUR_PROFIL_KODU_ELLE: ProfilKoduIsleyici(),
    TUR_EDEVLET_BARKODU: EdevletIsleyici(),
}
VARSAYILAN = KalemIsleyici()


def isleyici(tur: str) -> KararIsleyici:
    return ISLEYICILER.get(tur, VARSAYILAN)
