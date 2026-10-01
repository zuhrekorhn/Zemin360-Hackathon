"""Bugünkü Doğrulama'nın adaptörü (plan § 15, adım 1): karnenin başlangıç noktası.

Bugünkü davranışı olduğu gibi yeniden üretir, düzeltmez:
  - Yalnızca ilk link kanıtı okunur (`<head>` başlığı ve açıklaması); dosya,
    görsel, bağlı hesap ve kimlik bilgisi kullanılmaz.
  - Linksiz ve referanssız kalem puanlanmaz (bütün başlıklar "—").
  - Linksiz ama referansı yanıtlanmış kalemde Kanıt, Sonuç, Rol 0 yazılır
    (referans yanıtının açtığı sıfırlı gösterge, bulgu 17).
  - Referans yoksa Referans başlığı 0'dır ("—" değil, bulgu 19).

**Başlık ayrıştırması ayrı bir süreçte, süre sınırıyla çalışır.** İlk karnede
bugünkü `link_ozetini_cikar` iki vakada regex geri izlemesine düşüp sunucuyu
donduruyordu (bulgu 50, düzeltildi). Python'ın regex motoru eşleşme boyunca
GIL'i bırakmadığı için iş parçacığı yalıtımı yetmez. Yalıtım, ölçülen sistem
yeniden takılırsa karnenin de kilitlenmemesi için kalır: süre dolarsa işçi
öldürülür ve vaka "zaman_asimi" hatasıyla kaydedilir.
"""

from __future__ import annotations

import multiprocessing
from multiprocessing.pool import Pool
from types import TracebackType
from typing import Any

from app.agents.dogrulama import (
    LinkKontrolu,
    RubrikPuani,
    link_kontrolu,
    linki_kontrol_et,
    rubrik_puanla,
    ucuncu_taraf_onayi_hesapla,
)
from app.core.is_kalemi import birlesik_aciklama
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


class AyristirmaZamanAsimi(TimeoutError):
    """Başlık ayrıştırması süre sınırını aştı (işçi süreç öldürüldü)."""


def _ozgun_ayristirma(html: str) -> str:
    """İşçi süreçte çalışır: modülün kendi (yamalanmamış) fonksiyonu."""
    return link_kontrolu.link_ozetini_cikar(html)


class _YalitilmisAyristirici:
    """`link_ozetini_cikar`'ın yerine geçer: aynı işi işçi süreçte, süreyle yapar."""

    def __init__(self, sure: float) -> None:
        self._sure = sure
        self._havuz: Pool | None = None

    def _havuz_al(self) -> Pool:
        if self._havuz is None:
            self._havuz = multiprocessing.get_context("spawn").Pool(1)
        return self._havuz

    def __call__(self, html: str) -> str:
        is_ = self._havuz_al().apply_async(_ozgun_ayristirma, (html,))
        try:
            return is_.get(self._sure)
        except multiprocessing.TimeoutError as hata:
            self.kapat()
            raise AyristirmaZamanAsimi(f"başlık ayrıştırması {self._sure} sn'yi aştı") from hata

    def kapat(self) -> None:
        if self._havuz is not None:
            self._havuz.terminate()
            self._havuz.join()
            self._havuz = None


class MevcutSistemDegerlendirici:
    """Bağlam yöneticisi olarak kullanılır: girişte ayrıştırmayı yalıtır, çıkışta geri alır."""

    ad = "mevcut_sistem"

    def __init__(
        self, ag: AgKaseti, model: ModelKaseti, *, ayristirma_suresi: float = 20.0
    ) -> None:
        self._ag = ag
        self._model = model
        self._ayristirici = _YalitilmisAyristirici(ayristirma_suresi)
        self._ozgun = link_kontrolu.link_ozetini_cikar

    def __enter__(self) -> MevcutSistemDegerlendirici:
        link_kontrolu.link_ozetini_cikar = self._ayristirici
        return self

    def __exit__(
        self,
        tur: type[BaseException] | None,
        deger: BaseException | None,
        iz: TracebackType | None,
    ) -> None:
        link_kontrolu.link_ozetini_cikar = self._ozgun
        self._ayristirici.kapat()

    async def degerlendir(self, vaka: Vaka) -> Degerlendirme:
        referans_puanlari = [eski_olcege_cevir(r) for r in vaka.referanslar if r.yanitladi]
        ucuncu = ucuncu_taraf_onayi_hesapla(referans_puanlari)
        linkler = vaka.linkler

        if not linkler:
            if not referans_puanlari:
                return Degerlendirme(ayrinti={"neden": "linksiz kalem puanlanmaz"})
            return Degerlendirme(kanit=0, sonuc=0, rol=0, referans=ucuncu)

        try:
            kontrol = await linki_kontrol_et(linkler[0], transport=self._ag.transport())
        except AyristirmaZamanAsimi:
            return Degerlendirme(hata="zaman_asimi", ayrinti={"link": linkler[0]})

        puan = await self._rubrik(vaka, linkler[0], kontrol)
        return Degerlendirme(
            kanit=puan.kanit_orijinalligi,
            sonuc=puan.sonuc_olculebilirligi,
            rol=puan.rol_netligi,
            referans=ucuncu,
            not_metni=puan.gerekce_metni,
            ayrinti={"link_durumu": kontrol.aciklama, "link_ozeti": kontrol.ozet},
        )

    async def _rubrik(self, vaka: Vaka, link: str, kontrol: LinkKontrolu) -> RubrikPuani:
        aciklama = birlesik_aciklama(
            vaka.iddia.aciklama, vaka.iddia.olculebilir_sonuc, vaka.iddia.kendi_rolu
        )
        girdi: dict[str, Any] = {
            "baslik": vaka.iddia.baslik,
            "aciklama": aciklama,
            "kanit_linki": link,
            "erisilebilir": kontrol.erisilebilir,
            "link_durumu": kontrol.aciklama,
            "link_ozeti": kontrol.ozet,
        }

        async def gercek() -> dict[str, Any]:
            puan = await rubrik_puanla(
                baslik=vaka.iddia.baslik, aciklama=aciklama, kanit_linki=link, kontrol=kontrol
            )
            return puan.model_dump()

        return RubrikPuani.model_validate(
            await self._model.cagir("dogrulama_rubrik", girdi, gercek)
        )
