"""Uygulamadaki Doğrulama'nın adaptörü (plan § 15): karne her adımda bununla ölçer.

Uygulamanın yolunu izler: okuyucu zinciri (`okuma.kanit_oku`), uzun metinde
parça seçimi ve çekirdek (`cekirdek.kalemi_degerlendir`). Ağ, model ve embedding
yanıtları kasetten gelir. Uygulamanın henüz bilmediği girdiler kullanılmaz:
bağlı hesap (adım 8), dosya kanıtı (adım 9) ve referansın yapılandırılmış
yanıtları (adım 7).
"""

from __future__ import annotations

from typing import Any

from app.agents.dogrulama import ucuncu_taraf_onayi_hesapla
from app.agents.dogrulama.cekirdek import DegerlendirmeGirdisi, kalemi_degerlendir
from app.agents.dogrulama.cikarim import KanitCikarimi, cikar
from app.agents.dogrulama.hesap_sahipligi import BagliHesapBilgisi
from app.agents.dogrulama.okuma import kanit_oku
from app.core.embeddings import embedding_listesi_uret
from degerlendirme.degerlendirici import Degerlendirme
from degerlendirme.kaset import AgKaseti, ModelKaseti
from degerlendirme.vaka import ReferansGirdisi, Vaka

# 4 soruluk yanıtın bugünkü 1-5 ölçeğe çevrimi (adaptör varsayımı): yanıtlanan
# soruların ortalaması; hepsi "bilmiyorum" ise ölçeğin ortası.
_ESKI_OLCEK = {"evet": 5, "kismen": 3, "hayir": 1}


def eski_olcege_cevir(referans: ReferansGirdisi) -> int:
    yanitlar = [
        _ESKI_OLCEK[y]
        for y in (referans.iddia_dogru, referans.pay_dogru, referans.sonuc_dogru)
        if y in _ESKI_OLCEK
    ]
    if not yanitlar:
        return 3
    return int(sum(yanitlar) / len(yanitlar) + 0.5)


class MevcutSistemDegerlendirici:
    ad = "mevcut_sistem"

    def __init__(self, ag: AgKaseti, model: ModelKaseti, embedding: ModelKaseti) -> None:
        self._ag = ag
        self._model = model
        self._embedding = embedding

    async def degerlendir(self, vaka: Vaka) -> Degerlendirme:
        referans_puanlari = [eski_olcege_cevir(r) for r in vaka.referanslar if r.yanitladi]
        girdi = DegerlendirmeGirdisi(
            baslik=vaka.iddia.baslik,
            iddia_sahibi=vaka.kimlik.ad,
            aciklama=vaka.iddia.aciklama,
            sonuc=vaka.iddia.olculebilir_sonuc,
            pay=vaka.iddia.kendi_rolu,
            yetenekler=vaka.kart_yetenekleri,
        )
        sorgular = [f"{girdi.baslik} {girdi.aciklama or ''}", girdi.sonuc or "", girdi.pay or ""]
        bagli = tuple(
            BagliHesapBilgisi(h.saglayici, h.kullanici_adi, h.yontem)
            for h in vaka.kimlik.bagli_hesaplar
        )
        okunanlar = [
            await kanit_oku(
                link,
                sorgular,
                bagli_hesaplar=bagli,
                transport=self._ag.transport(),
                gom=self._gom,
            )
            for link in vaka.linkler
        ]
        sonuc = await kalemi_degerlendir(girdi, okunanlar, self._cikar)
        okunan = okunanlar[0] if okunanlar else None
        return Degerlendirme(
            kanit=sonuc.puanlar.kanit,
            sonuc=sonuc.puanlar.sonuc,
            rol=sonuc.puanlar.rol,
            referans=ucuncu_taraf_onayi_hesapla(referans_puanlari),
            not_metni=sonuc.not_metni,
            ayrinti={
                "erisim": okunan.erisim.value if okunan else None,
                "platform": okunan.platform if okunan else None,
                "seviye": okunan.seviye.value if okunan else None,
            },
        )

    async def _cikar(self, alanlar: dict[str, str]) -> KanitCikarimi:
        async def gercek() -> dict[str, Any]:
            return (await cikar(alanlar)).model_dump()

        return KanitCikarimi.model_validate(
            await self._model.cagir("dogrulama_cikarim", alanlar, gercek)
        )

    async def _gom(self, metinler: list[str], tur: str) -> list[list[float]]:
        async def gercek() -> dict[str, Any]:
            vektorler = await embedding_listesi_uret(metinler, tur)  # type: ignore[arg-type]
            return {"v": [[round(x, 6) for x in v] for v in vektorler]}

        kayit = await self._embedding.cagir("voyage", {"metinler": metinler, "tur": tur}, gercek)
        return kayit["v"]
