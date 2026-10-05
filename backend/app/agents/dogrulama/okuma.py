"""Kanıt adresinin okunması ve değerlendirmeye hazırlanması (plan § 5).

Okuyucu zinciri (`app/core/kanit_okuma/`) belgeyi verir; burada çekirdeğin
girdisine (`OkunanKanit`) çevrilir ve uzun metinde modelin göreceği parçalar
iddiaya göre seçilir (§ 5.4). Alıntı denetimi yine tam metne yapılır.
Herkese açık okunan çalışma seviye C'dir; gencin bağlı hesabında duruyorsa B
(`hesap_sahipligi.py`).

Yedek okuyucu ekran görüntüsü aldıysa (§ 5.5) görüntüler yüklenen görsel gibi
okunur (§ 4.3): model görülen metni ve betimi yazar, alıntı denetimi sayfanın
metnine ve görselde yazan metne yapılır, betime değil. Seviye yine linkin
seviyesidir (C; bağlı hesapta B), yüklenen görsel gibi D değil. Okunuş adres
başına 24 saat saklanır (`onbellek.py`).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence

import httpx

from app.agents.dogrulama.capalar import CapaSonucu
from app.agents.dogrulama.dosya_cikarimi import DosyaOkunusu, ekranlari_oku
from app.agents.dogrulama.hesap_sahipligi import BagliHesapBilgisi, sahiplik_belirle
from app.agents.dogrulama.kurallar import OkunanKanit
from app.core.dis_servisler import kurulum
from app.core.dis_servisler.uzak_okuyucu import UzakOkuyucu
from app.core.dis_servisler.yedek_okuyucu import YedekOkuyucu
from app.core.embeddings import embedding_listesi_uret
from app.core.kanit_okuma import kaniti_oku
from app.core.kanit_okuma.belge import ErisimDurumu, KanitBelgesi, ParcaTuru
from app.core.kanit_okuma.onbellek import ZamanliOnbellek
from app.core.kanit_okuma.parca_secimi import Gomucu, sec

logger = logging.getLogger("zemin360.dogrulama")

EkranOkuyucu = Callable[[Sequence[bytes]], Awaitable[DosyaOkunusu]]

# Adres → ekran görüntülerinin okunuşu (testler her testte boşaltır).
EKRAN_OKUNUSLARI: ZamanliOnbellek[DosyaOkunusu] = ZamanliOnbellek()


async def kanit_oku(
    url: str,
    iddia_sorgulari: list[str],
    *,
    bagli_hesaplar: Sequence[BagliHesapBilgisi] = (),
    transport: httpx.AsyncBaseTransport | None = None,
    gom: Gomucu = embedding_listesi_uret,
    yedek: YedekOkuyucu | None = None,
    uzak: UzakOkuyucu | None = None,
    ekran_oku: EkranOkuyucu = ekranlari_oku,
) -> OkunanKanit:
    """`yedek` ve `uzak` verilmezse kurulum noktasındakiler kullanılır (değerlendirme
    seti kayıtlı yedek okuyucuyu ve kapalı uzak okuyucuyu verir)."""
    belge = await kaniti_oku(
        url,
        transport=transport,
        yedek=yedek if yedek is not None else kurulum.yedek_okuyucu(),
        uzak=uzak if uzak is not None else kurulum.uzak_okuyucu(),
    )
    ekran = await _ekran_okunusu(belge, ekran_oku)
    erisim, metin, alinti = _ekranla_birlestir(belge, ekran)
    model_metni = await sec(metin, iddia_sorgulari, gom) if metin else ""
    sahiplik = sahiplik_belirle(belge, bagli_hesaplar)
    return OkunanKanit(
        erisim=erisim,
        seviye=sahiplik.seviye,
        metin=metin,
        url=url,
        bireysel=sahiplik.bireysel,
        platform=belge.platform,
        model_metni=model_metni,
        platform_metni=belge.platform_metni,
        sahiplik_kaynagi=sahiplik.kaynak,
        alinti_metni=alinti,
        okuyucu=belge.okuyucu,
    )


async def _ekran_okunusu(belge: KanitBelgesi, oku: EkranOkuyucu) -> DosyaOkunusu | None:
    if not belge.ekran_goruntuleri:
        return None
    onceki = EKRAN_OKUNUSLARI.al(belge.url)
    if onceki is not None:
        return onceki
    try:
        okunus = await oku(belge.ekran_goruntuleri)
    except Exception as hata:  # zarif düşüş: görüntüsüz okunuşla devam (sinyal "—" olabilir)
        logger.warning("ekran goruntusu okunamadi tur=%s", type(hata).__name__)
        return None
    EKRAN_OKUNUSLARI.koy(belge.url, okunus)
    return okunus


def _ekranla_birlestir(
    belge: KanitBelgesi, ekran: DosyaOkunusu | None
) -> tuple[ErisimDurumu, str, str | None]:
    """(erişim, modelin metni, alıntı kaynağı). Görüntüsüz okunuş olduğu gibi kalır."""
    if ekran is None:
        return belge.erisim, belge.metin, None
    yazili = "\n\n".join(m for m in (belge.metin, ekran.gorsel_metni.strip()) if m)
    betim = ekran.betim.strip()
    satirlar = [f"[Görülen: {betim}]"] if betim else []
    metin = "\n".join([*satirlar, *([yazili] if yazili else [])])
    erisim = ErisimDurumu.ACIK if metin else belge.erisim
    return erisim, metin, yazili


async def dosya_okunusu(
    *,
    tur: str,
    dosya_adi: str | None,
    tam_metin: str | None,
    betim: str | None,
    capa: CapaSonucu,
    iddia_sorgulari: list[str],
    gom: Gomucu = embedding_listesi_uret,
) -> OkunanKanit:
    """Yüklenmiş dosyanın değerlendirme girdisi (plan § 4). Dosya yüklenirken bir kez
    okunmuştur (`servisler/dogrulama/dosyalar.py`); burada ağ ve model yok.

    Model betimi ve metni birlikte görür (görselin çalışmayla ilgisi betimden
    anlaşılır); alıntı denetimi yalnızca belgede yazan metne yapılır. Seviye
    çapalardan gelir (`capalar.dosya_seviyesi`), çapasız dosya D.
    """
    yazili = (tam_metin or "").strip()
    satirlar = [f"[Görülen: {betim.strip()}]"] if betim and betim.strip() else []
    if yazili:
        satirlar.append(yazili)
    metin = "\n".join(satirlar)
    model_metni = await sec(metin, iddia_sorgulari, gom) if metin else ""
    return OkunanKanit(
        erisim=ErisimDurumu.ACIK if metin else ErisimDurumu.ICERIK_YOK,
        seviye=capa.seviye,
        sahiplik_kaynagi=capa.sahiplik,
        metin=metin,
        platform="pdf" if tur == ParcaTuru.DOSYA.value else "gorsel",
        model_metni=model_metni,
        tur=tur,
        alinti_metni=yazili,
        dosya_adi=dosya_adi,
    )
