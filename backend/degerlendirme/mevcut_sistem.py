"""Uygulamadaki Doğrulama'nın adaptörü (docs/dogrulama.md § 15): karne her adımda bununla ölçer.

Uygulamanın yolunu izler: okuyucu zinciri ve yedek okuyucu (`okuma.kanit_oku`),
dosya hattı (`dosya_hatti` → `dosyalar.dosyayi_isle` → `okuma.dosya_okunusu`), uzun
metinde parça seçimi ve çekirdek (`cekirdek.kalemi_degerlendir`). Ağ, yedek okuyucu,
model ve embedding yanıtları kasetten gelir. Kanıtlar vakadaki sırayla okunur (link ve dosya).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

from app.agents.dogrulama import ucuncu_taraf_onayi_hesapla
from app.agents.dogrulama.capalar import KimlikDurumu, dosya_seviyesi
from app.agents.dogrulama.cekirdek import DegerlendirmeGirdisi, kalemi_degerlendir
from app.agents.dogrulama.cikarim import KanitCikarimi, cikar
from app.agents.dogrulama.dosya_cikarimi import DosyaOkunusu, dosyayi_oku, ekranlari_oku
from app.agents.dogrulama.hesap_sahipligi import BagliHesapBilgisi
from app.agents.dogrulama.kurallar import OkunanKanit
from app.agents.dogrulama.okuma import dosya_okunusu, kanit_oku
from app.core.dis_servisler.uzak_okuyucu import KapaliUzakOkuyucu
from app.core.dis_servisler.virus import KapaliTarayici
from app.core.dosya_hatti import dosyayi_hazirla
from app.core.embeddings import embedding_listesi_uret
from app.servisler.dogrulama.dosyalar import dosyayi_isle
from degerlendirme.degerlendirici import Degerlendirme
from degerlendirme.kaset import AgKaseti, ModelKaseti, YedekOkuyucuKaseti
from degerlendirme.vaka import SETI_KLASORU, ReferansGirdisi, Vaka

DOSYA_KLASORU = SETI_KLASORU / "dosyalar"

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

    def __init__(
        self,
        ag: AgKaseti,
        model: ModelKaseti,
        embedding: ModelKaseti,
        yedek: YedekOkuyucuKaseti,
    ) -> None:
        self._ag = ag
        self._model = model
        self._embedding = embedding
        self._yedek = yedek

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
        kimlik = KimlikDurumu(
            eposta_dogrulandi=vaka.kimlik.eposta_dogrulandi,
            ad_kilitli=vaka.kimlik.eposta_dogrulandi,
        )
        okunanlar = []
        for kanit in vaka.kanitlar:
            if kanit.tur == "link" and kanit.url:
                okunanlar.append(
                    await kanit_oku(
                        kanit.url,
                        sorgular,
                        bagli_hesaplar=bagli,
                        transport=self._ag.transport(),
                        gom=self._gom,
                        yedek=self._yedek,
                        # Üçüncü taraf okuma karnede yok (bayrak varsayılan kapalı).
                        uzak=KapaliUzakOkuyucu(),
                        ekran_oku=self._ekranlari_oku,
                    )
                )
            elif kanit.dosya:
                okunanlar.append(await self._dosya_okunusu(vaka, kanit.dosya, sorgular, kimlik))
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

    async def _dosya_okunusu(
        self, vaka: Vaka, yol: str, sorgular: list[str], kimlik: KimlikDurumu
    ) -> OkunanKanit:
        hazir = await dosyayi_hazirla((DOSYA_KLASORU / yol).read_bytes(), KapaliTarayici())
        islenmis = await dosyayi_isle(
            hazir,
            yol,
            ad=vaka.kimlik.ad,
            eposta=vaka.kimlik.eposta,
            oku=self._dosya_oku,
            transport=self._ag.transport(),
        )
        return await dosya_okunusu(
            tur=hazir.parca_turu.value,
            dosya_adi=yol,
            tam_metin=islenmis.icerik.tam_metin,
            betim=islenmis.icerik.betim,
            capa=dosya_seviyesi(islenmis.belge, kimlik),
            iddia_sorgulari=sorgular,
            gom=self._gom,
        )

    async def _dosya_oku(self, veri: bytes, icerik_turu: str) -> DosyaOkunusu:
        async def gercek() -> dict[str, Any]:
            return (await dosyayi_oku(veri, icerik_turu)).model_dump()

        girdi = {"ozet": hashlib.sha256(veri).hexdigest(), "tur": icerik_turu}
        return DosyaOkunusu.model_validate(
            await self._model.cagir("dogrulama_dosya_okuma", girdi, gercek)
        )

    async def _ekranlari_oku(self, goruntuler: Sequence[bytes]) -> DosyaOkunusu:
        async def gercek() -> dict[str, Any]:
            return (await ekranlari_oku(goruntuler)).model_dump()

        girdi = {"ozet": hashlib.sha256(b"".join(goruntuler)).hexdigest(), "tur": "ekran"}
        return DosyaOkunusu.model_validate(
            await self._model.cagir("dogrulama_dosya_okuma", girdi, gercek)
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
