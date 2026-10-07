"""e-Devlet barkodu çapası (docs/dogrulama.md § 4.2): GİRVAK elle doğrular.

Doğrulayıcı yalnızca barkodu kaydeder (`girvak_karari: None` → D). Dosya
eklenince `edevlet_barkodu` işareti açılır (`isaret_ac`); GİRVAK kararı çapaya
yazılır ve kalem yeniden değerlendirilir (`EdevletIsleyici`). Onay → A.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.agents.dogrulama.capalar import TUR_EDEVLET
from app.agents.inceleme_durumu import KAPANDI
from app.core.capalar.edevlet import edevlet_barkodu
from app.models.bildirim import TUR_INCELEME_SONUCU
from app.models.guven_skoru import GuvenSkoru
from app.models.inceleme_isareti import TUR_EDEVLET_BARKODU, IncelemeIsareti
from app.models.kanit_parcasi import KanitParcasi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler import inceleme
from app.servisler.dogrulama.capalar.temel import CapaGirdisi

ONAYLANDI = "onaylandi"
REDDEDILDI = "reddedildi"


class EdevletDogrulayici:
    ad = TUR_EDEVLET

    async def dogrula(self, girdi: CapaGirdisi) -> list[dict[str, Any]]:
        barkod = edevlet_barkodu(girdi.metin)
        return [{"tur": TUR_EDEVLET, "barkod": barkod, "girvak_karari": None}] if barkod else []


def _birlestir(eski: dict[str, Any], yeni: dict[str, Any]) -> dict[str, Any]:
    return {**eski, "parcalar": [*eski.get("parcalar", []), *yeni["parcalar"]]}


async def inceleme_ac(
    oturum: AsyncSession, parca: KanitParcasi, cikti: SomutCikti, kullanici_id: uuid.UUID
) -> None:
    """Parçada e-Devlet barkodu varsa GİRVAK kuyruğuna. Kalem başına tek açık işaret;
    aynı kalemin ikinci belgesi açık işaretin ayrıntısına eklenir."""
    barkodlar = [
        c["barkod"] for c in (parca.belge or {}).get("capalar", []) if c.get("tur") == TUR_EDEVLET
    ]
    if not barkodlar:
        return
    if parca.id is None:
        await oturum.flush()
    await inceleme.isaret_ac(
        oturum,
        TUR_EDEVLET_BARKODU,
        kullanici_id,
        somut_cikti_id=cikti.id,
        ayrinti={"parcalar": [{"parca_id": str(parca.id), "barkod": b} for b in barkodlar]},
        birlestir=_birlestir,
    )


class EdevletIsleyici:
    """GİRVAK kararı çapaya yazılır; kalem yeniden değerlendirilir, genç bilgilendirilir."""

    async def uygula(
        self, oturum: AsyncSession, isaret: IncelemeIsareti, karar: str
    ) -> inceleme.KararEtkisi:
        sonuc = ONAYLANDI if karar == KAPANDI else REDDEDILDI
        idler = [uuid.UUID(p["parca_id"]) for p in isaret.ayrinti.get("parcalar", [])]
        parcalar = list(
            await oturum.scalars(select(KanitParcasi).where(KanitParcasi.id.in_(idler)))
        )
        for parca in parcalar:
            belge = dict(parca.belge or {})
            belge["capalar"] = [
                {**c, "girvak_karari": sonuc} if c.get("tur") == TUR_EDEVLET else c
                for c in belge.get("capalar", [])
            ]
            parca.belge = belge
            flag_modified(parca, "belge")

        cikti = await oturum.get(SomutCikti, isaret.somut_cikti_id)
        arka_plan: tuple[inceleme.ArkaPlanIsi, ...] = ()
        if cikti is not None and parcalar:
            # Kalem "değerlendirilmedi"ye döner; kart hazırlama yeni kararla puanlar.
            await oturum.execute(
                update(GuvenSkoru)
                .where(GuvenSkoru.somut_cikti_id == cikti.id)
                .values(degerlendirme_tarihi=None)
            )
            # Tembel import: kart_hazirlama → api.yetenek_kartlari → dosyalar →
            # capalar zinciri modül yüklenirken döngü kuruyordu (test dosyası tek
            # başına çalışınca ImportError).
            from app.servisler import kart_hazirlama

            kart = await oturum.get(YetenekKarti, cikti.yetenek_karti_id)
            arka_plan = (
                inceleme.ArkaPlanIsi(kart_hazirlama.karti_hazirla, (kart.id, kart.versiyon)),
            )
        ad = f"“{cikti.baslik}” çalışmandaki" if cikti else "yüklediğin"
        if sonuc == ONAYLANDI:
            metin = f"GİRVAK {ad} e-Devlet belgesini doğruladı."
        else:
            metin = (
                f"GİRVAK {ad} e-Devlet belgesini doğrulayamadı. Barkodun okunaklı "
                "olduğundan emin olup belgeyi yeniden yükleyebilirsin."
            )
        if isaret.girvak_notu:
            metin += f" GİRVAK'ın notu: {isaret.girvak_notu}"
        return inceleme.KararEtkisi(
            bildirim_turu=TUR_INCELEME_SONUCU, bildirim_metni=metin, arka_plan=arka_plan
        )
