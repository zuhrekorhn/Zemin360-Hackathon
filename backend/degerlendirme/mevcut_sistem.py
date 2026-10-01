"""Uygulamadaki Doğrulama'nın adaptörü (plan § 15): karne her adımda bununla ölçer.

Uygulamanın o anki davranışını yeniden üretir, düzeltmez. Adım 4'teki yeni
puan çekirdeği gelene kadar:
  - Yalnızca ilk link kanıtı okunur (`<head>` başlığı ve açıklaması); dosya,
    görsel, bağlı hesap ve kimlik bilgisi kullanılmaz.
  - Linksiz ve referanssız kalem puanlanmaz (bütün başlıklar "—").
  - Linksiz ama referansı yanıtlanmış kalemde yalnızca Referans dolar
    (adım 3'ten beri; önceden Kanıt, Sonuç, Rol 0 yazılıyordu, bulgu 17).
  - Yanıt yoksa Referans "—" (adım 3'ten beri; önceden 0'dı, bulgu 19).

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

from app.agents.dogrulama import link_kontrolu, linki_kontrol_et, ucuncu_taraf_onayi_hesapla
from app.agents.dogrulama.cekirdek import DegerlendirmeGirdisi, kalemi_degerlendir
from app.agents.dogrulama.cikarim import KanitCikarimi, cikar
from app.agents.dogrulama.link_kontrolu import okunan_kanit
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
        """Uygulamanın çekirdeğiyle (cekirdek.kalemi_degerlendir) aynı yol.

        Uygulamanın bugün bilmediği girdiler kullanılmaz: bağlı hesap (adım 8),
        dosya kanıtı (adım 9) ve referansın yapılandırılmış yanıtları (adım 7).
        """
        referans_puanlari = [eski_olcege_cevir(r) for r in vaka.referanslar if r.yanitladi]
        ucuncu = ucuncu_taraf_onayi_hesapla(referans_puanlari)
        link = vaka.linkler[0] if vaka.linkler else None

        okunan = None
        if link is not None:
            try:
                kontrol = await linki_kontrol_et(link, transport=self._ag.transport())
            except AyristirmaZamanAsimi:
                return Degerlendirme(hata="zaman_asimi", ayrinti={"link": link})
            okunan = okunan_kanit(kontrol, link)

        girdi = DegerlendirmeGirdisi(
            baslik=vaka.iddia.baslik,
            aciklama=vaka.iddia.aciklama,
            sonuc=vaka.iddia.olculebilir_sonuc,
            pay=vaka.iddia.kendi_rolu,
            yetenekler=vaka.kart_yetenekleri,
        )
        sonuc = await kalemi_degerlendir(girdi, okunan, self._cikar)
        return Degerlendirme(
            kanit=sonuc.puanlar.kanit,
            sonuc=sonuc.puanlar.sonuc,
            rol=sonuc.puanlar.rol,
            referans=ucuncu,
            not_metni=sonuc.not_metni,
            ayrinti={"erisim": okunan.erisim.value if okunan else None},
        )

    async def _cikar(self, alanlar: dict[str, str]) -> KanitCikarimi:
        async def gercek() -> dict[str, Any]:
            return (await cikar(alanlar)).model_dump()

        return KanitCikarimi.model_validate(
            await self._model.cagir("dogrulama_cikarim", alanlar, gercek)
        )
