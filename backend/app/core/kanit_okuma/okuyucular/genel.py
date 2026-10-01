"""Genel okuyucu: her adres için son durak (sayfa → HTML özeti → erişim durumu)."""

from __future__ import annotations

import httpx

from app.core.kanit_okuma.belge import ErisimDurumu, KanitBelgesi
from app.core.kanit_okuma.erisim import erisim_durumu, hata_durumu
from app.core.kanit_okuma.html_ozeti import html_ozeti
from app.core.kanit_okuma.istek import Sayfa, getir
from app.core.kanit_okuma.okuyucu import OkumaBaglami, metni_kur


def sayfadan_belge(url: str, sayfa: Sayfa, platform: str = "web") -> KanitBelgesi:
    """Getirilmiş bir sayfayı belgeye çevirir (Google okuyucusu da kullanır)."""
    tur = sayfa.icerik_turu.lower()
    if "pdf" in tur:
        # PDF içeriği dosya hattında okunur (adım 9); bugün içerik okunamadı.
        return KanitBelgesi(url=url, erisim=ErisimDurumu.ICERIK_YOK, platform="pdf")
    if "html" in tur or not tur:
        ozet = html_ozeti(sayfa.metin)
        baslik, govde = ozet.gorunen_baslik, ozet.metin
        metin = metni_kur(
            ("Başlık", baslik),
            ("Açıklama", ozet.aciklama),
            ("Yazarlar", ", ".join(ozet.yazarlar)),
            govde=govde,
        )
        yazarlar = tuple(ozet.yazarlar)
    else:  # düz metin, CSV
        baslik, govde, metin, yazarlar = None, sayfa.metin, sayfa.metin, ()
    erisim = erisim_durumu(
        # Başlık ve açıklama da içeriktir: JavaScript ile çizilen sayfanın gövdesi boş
        # olsa bile meta bilgisi çalışmayı anlatabilir (Kaggle, Behance önizlemesi).
        durum=sayfa.durum,
        son_url=sayfa.son_url,
        baslik=baslik,
        metin_uzunlugu=len(metin),
    )
    return KanitBelgesi(
        url=url,
        erisim=erisim,
        platform=platform,
        baslik=baslik,
        metin=metin if erisim is ErisimDurumu.ACIK else "",
        yazarlar=yazarlar,
    )


class GenelOkuyucu:
    ad = "genel"

    def uygun_mu(self, url: httpx.URL) -> bool:
        return True

    async def oku(self, url: httpx.URL, baglam: OkumaBaglami) -> KanitBelgesi:
        try:
            sayfa = await getir(str(url), transport=baglam.transport)
        except Exception as hata:  # nedeni durum olur; bilinmeyen hata yeniden fırlar
            return KanitBelgesi(url=str(url), erisim=hata_durumu(hata))
        return sayfadan_belge(str(url), sayfa)
