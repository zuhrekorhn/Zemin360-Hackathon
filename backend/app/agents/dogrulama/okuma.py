"""Kanıt adresinin okunması ve değerlendirmeye hazırlanması (plan § 5).

Okuyucu zinciri (`app/core/kanit_okuma/`) belgeyi verir; burada çekirdeğin
girdisine (`OkunanKanit`) çevrilir ve uzun metinde modelin göreceği parçalar
iddiaya göre seçilir (§ 5.4). Alıntı denetimi yine tam metne yapılır.
Herkese açık okunan çalışma seviye C'dir; gencin bağlı hesabında duruyorsa B
(`hesap_sahipligi.py`).
"""

from __future__ import annotations

from collections.abc import Sequence

import httpx

from app.agents.dogrulama.hesap_sahipligi import BagliHesapBilgisi, sahiplik_belirle
from app.agents.dogrulama.kurallar import OkunanKanit
from app.core.embeddings import embedding_listesi_uret
from app.core.kanit_okuma import kaniti_oku
from app.core.kanit_okuma.belge import ErisimDurumu, KaynakSeviyesi, ParcaTuru
from app.core.kanit_okuma.parca_secimi import Gomucu, sec


async def kanit_oku(
    url: str,
    iddia_sorgulari: list[str],
    *,
    bagli_hesaplar: Sequence[BagliHesapBilgisi] = (),
    transport: httpx.AsyncBaseTransport | None = None,
    gom: Gomucu = embedding_listesi_uret,
) -> OkunanKanit:
    belge = await kaniti_oku(url, transport=transport)
    model_metni = await sec(belge.metin, iddia_sorgulari, gom) if belge.metin else ""
    sahiplik = sahiplik_belirle(belge, bagli_hesaplar)
    return OkunanKanit(
        erisim=belge.erisim,
        seviye=sahiplik.seviye,
        metin=belge.metin,
        url=url,
        bireysel=sahiplik.bireysel,
        platform=belge.platform,
        model_metni=model_metni,
        platform_metni=belge.platform_metni,
        sahiplik_kaynagi=sahiplik.kaynak,
    )


async def dosya_okunusu(
    *,
    tur: str,
    dosya_adi: str | None,
    tam_metin: str | None,
    betim: str | None,
    seviye: KaynakSeviyesi,
    iddia_sorgulari: list[str],
    gom: Gomucu = embedding_listesi_uret,
) -> OkunanKanit:
    """Yüklenmiş dosyanın değerlendirme girdisi (plan § 4). Dosya yüklenirken bir kez
    okunmuştur (`servisler/dogrulama/dosyalar.py`); burada ağ ve model yok.

    Model betimi ve metni birlikte görür (görselin çalışmayla ilgisi betimden
    anlaşılır); alıntı denetimi yalnızca belgede yazan metne yapılır.
    """
    yazili = (tam_metin or "").strip()
    satirlar = [f"[Görülen: {betim.strip()}]"] if betim and betim.strip() else []
    if yazili:
        satirlar.append(yazili)
    metin = "\n".join(satirlar)
    model_metni = await sec(metin, iddia_sorgulari, gom) if metin else ""
    return OkunanKanit(
        erisim=ErisimDurumu.ACIK if metin else ErisimDurumu.ICERIK_YOK,
        seviye=seviye,
        metin=metin,
        platform="pdf" if tur == ParcaTuru.DOSYA.value else "gorsel",
        model_metni=model_metni,
        tur=tur,
        alinti_metni=yazili,
        dosya_adi=dosya_adi,
    )
