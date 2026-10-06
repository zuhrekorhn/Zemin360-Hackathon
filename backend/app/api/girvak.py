"""GİRVAK paneli (docs/faz-b-kimlik-ve-dongu.md § 7).

Firma akışı: firma doğrulaması (docs/plans/firma-akisi.md § 6). GİRVAK'ın
yazabildiği tek şey doğrulama kararı.

Faz B'de yalnızca sayılar: hesap, kart, eşleşme, iş birliği. Hedefler ve
grafikler Faz D'de bu uca eklenecek. Kişisel veri dönmez, yalnızca sayım.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.eslestirme import (
    DURUM_GENC_ILGILENDI,
    DURUM_ILGILENILIYOR,
    DURUM_KABUL_EDILDI,
    DURUM_KAPANDI,
    DURUM_ONERILDI,
    DURUM_REDDEDILDI,
)
from app.agents.takip_durumu import (
    ISBIRLIGI_AKTIF,
    ISBIRLIGI_PLAN_BEKLIYOR,
    ISBIRLIGI_TAMAMLANDI,
)
from app.agents.uygunluk import gorunur_kosulu
from app.api.bildirimler import bildirim_ekle
from app.api.kimlik import rol_gerekli
from app.api.sahiplik import bulunamadi
from app.core import firma_dogrulama
from app.core.program import HEDEFLER
from app.db.session import get_session
from app.models.bildirim import TUR_FIRMA_DOGRULANDI
from app.models.eslesme import Eslesme
from app.models.hesap import ROL_GENC, ROL_GIRVAK, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.isbirligi import Isbirligi
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.models.yetenek_karti import YetenekKarti
from app.schemas.girvak import (
    EslesmeKirilimi,
    EslesmeSayilari,
    FirmaDogrulamaIstegi,
    HedefSayisi,
    HesapSayilari,
    IsbirligiSayilari,
    KapananIhtiyaclar,
    OnayBekleyenFirma,
    Sayilar,
    TurSayilari,
)
from app.servisler.ilgi import IHTIYAC_KAPANDI

router = APIRouter(prefix="/girvak", tags=["girvak"])


async def _say(oturum: AsyncSession, model) -> int:
    return await oturum.scalar(select(func.count()).select_from(model))


async def _gruplu(oturum: AsyncSession, kolon, *kosullar) -> dict[str, int]:
    satirlar = await oturum.execute(select(kolon, func.count()).where(*kosullar).group_by(kolon))
    return {deger: sayi for deger, sayi in satirlar.all()}


@router.get("/sayilar", response_model=Sayilar)
async def sayilar(
    _hesap: Hesap = Depends(rol_gerekli(ROL_GIRVAK)),
    oturum: AsyncSession = Depends(get_session),
) -> Sayilar:
    roller = await _gruplu(oturum, Hesap.rol)
    durumlar = await _gruplu(oturum, Eslesme.durum, gorunur_kosulu())
    isbirlikleri = await _gruplu(oturum, Isbirligi.durum)
    return Sayilar(
        hesap=HesapSayilari(
            genc=roller.get(ROL_GENC, 0),
            kurum=roller.get(ROL_KURUM, 0),
            girvak=roller.get(ROL_GIRVAK, 0),
        ),
        yetenek_karti=await _say(oturum, YetenekKarti),
        ihtiyac_karti=await _say(oturum, IhtiyacKarti),
        eslesme=EslesmeSayilari(
            onerildi=durumlar.get(DURUM_ONERILDI, 0),
            ilgileniliyor=durumlar.get(DURUM_ILGILENILIYOR, 0),
            kabul_edildi=durumlar.get(DURUM_KABUL_EDILDI, 0),
            reddedildi=durumlar.get(DURUM_REDDEDILDI, 0),
            genc_ilgilendi=durumlar.get(DURUM_GENC_ILGILENDI, 0),
            kapandi=durumlar.get(DURUM_KAPANDI, 0),
        ),
        isbirligi=await _say(oturum, Isbirligi),
        isbirligi_durumlari=IsbirligiSayilari(
            plan_bekliyor=isbirlikleri.get(ISBIRLIGI_PLAN_BEKLIYOR, 0),
            aktif=isbirlikleri.get(ISBIRLIGI_AKTIF, 0),
            tamamlandi=isbirlikleri.get(ISBIRLIGI_TAMAMLANDI, 0),
        ),
        hedefler=await hedef_sayilari(oturum, durumlar, isbirlikleri),
        kapanan_ihtiyaclar=await kapanan_ihtiyaclar(oturum),
        kirilim=await eslesme_kirilimi(oturum),
    )


async def eslesme_kirilimi(oturum: AsyncSession) -> EslesmeKirilimi:
    """Genç–firma ve firma–firma ayrı sayılır (docs/plans/firma-akisi.md § 0 karar 19)."""
    firma_mi = Eslesme.firma_karti_id.isnot(None).label("firma_mi")
    eslesmeler = await oturum.execute(
        select(firma_mi, Eslesme.durum, func.count())
        .where(gorunur_kosulu())
        .group_by(firma_mi, Eslesme.durum)
    )
    isbirlikleri = await oturum.execute(
        select(firma_mi, Isbirligi.durum, func.count())
        .join(Eslesme, Isbirligi.eslesme_id == Eslesme.id)
        .group_by(firma_mi, Isbirligi.durum)
    )
    sayilar = {False: TurSayilari(), True: TurSayilari()}
    for firma, durum, sayi in eslesmeler.all():
        if durum == DURUM_ONERILDI:
            sayilar[firma].oneri += sayi
        elif durum == DURUM_KABUL_EDILDI:
            sayilar[firma].karsilikli_ilgi += sayi
    for firma, durum, sayi in isbirlikleri.all():
        sayilar[firma].isbirligi += sayi
        if durum == ISBIRLIGI_TAMAMLANDI:
            sayilar[firma].tamamlanan += sayi
    return EslesmeKirilimi(genc_firma=sayilar[False], firma_firma=sayilar[True])


async def kapanan_ihtiyaclar(oturum: AsyncSession) -> KapananIhtiyaclar:
    satirlar = await oturum.execute(
        select(IhtiyacKarti.kapanma_nedeni, func.count())
        .where(IhtiyacKarti.durum == IHTIYAC_KAPANDI)
        .group_by(IhtiyacKarti.kapanma_nedeni)
    )
    nedenler = {neden or "nedensiz": sayi for neden, sayi in satirlar.all()}
    return KapananIhtiyaclar(**nedenler)


async def hedef_sayilari(
    oturum: AsyncSession, eslesme_durumlari: dict[str, int], isbirligi_durumlari: dict[str, int]
) -> list[HedefSayisi]:
    """Program hedefleri, platformdaki ölçümleriyle (docs/faz-d-canlilik.md § 7).

    Yalnızca hesabı olan profiller sayılır (Faz B öncesi profil programın
    katılımcısı değil).
    """
    basvuru = await oturum.scalar(
        select(func.count(func.distinct(YetenekKarti.kullanici_id)))
        .join(Kullanici, Kullanici.id == YetenekKarti.kullanici_id)
        .where(Kullanici.hesap_id.isnot(None))
    )
    kurum = await oturum.scalar(
        select(func.count(func.distinct(IhtiyacKarti.kurum_id)))
        .join(Kurum, Kurum.id == IhtiyacKarti.kurum_id)
        .where(Kurum.hesap_id.isnot(None))
    )
    sayilar = {
        "basvuru": basvuru,
        "kurum": kurum,
        "eslesme": eslesme_durumlari.get(DURUM_KABUL_EDILDI, 0),
        "pilot": isbirligi_durumlari.get(ISBIRLIGI_TAMAMLANDI, 0),
    }
    return [
        HedefSayisi(
            anahtar=h.anahtar,
            program_adi=h.program_adi,
            olcum=h.olcum,
            sayi=sayilar[h.anahtar],
            hedef=h.hedef,
        )
        for h in HEDEFLER
    ]


# --- Firma doğrulaması (docs/plans/firma-akisi.md § 0 karar 6, § 6) -------------------

FIRMA_BULUNAMADI = "Firma bulunamadı"
DOGRULANDI_METNI = (
    "Firmanız doğrulandı. Adınızın yanında artık “Doğrulanmış firma” işareti görünüyor."
)


def _firma_satiri(kurum: Kurum, kayit_tarihi: dt.datetime) -> OnayBekleyenFirma:
    return OnayBekleyenFirma(
        kurum_id=kurum.id,
        ad=kurum.ad,
        tur=kurum.tur,
        sektor=kurum.sektor,
        sehir=kurum.sehir,
        web_sitesi=kurum.web_sitesi,
        eposta_alan_adi=firma_dogrulama.eposta_alan_adi(kurum.iletisim_email),
        ipucu=firma_dogrulama.alan_adi_ipucu(kurum.iletisim_email, kurum.web_sitesi),
        dogrulama_durumu=kurum.dogrulama_durumu,
        dogrulama_tarihi=kurum.dogrulama_tarihi,
        kayit_tarihi=kayit_tarihi,
    )


@router.get("/firmalar", response_model=list[OnayBekleyenFirma])
async def firmalar(
    durum: Literal["bekliyor", "dogrulandi", "simdilik_degil"] = "bekliyor",
    _hesap: Hesap = Depends(rol_gerekli(ROL_GIRVAK)),
    oturum: AsyncSession = Depends(get_session),
) -> list[OnayBekleyenFirma]:
    """Doğrulama durumuna göre firmalar (varsayılan: onay bekleyenler), en yeni kayıt önce.

    Yalnızca hesabı olan firmalar (Faz B öncesi profil programın katılımcısı değil).
    """
    satirlar = await oturum.execute(
        select(Kurum, Hesap.olusturma_tarihi)
        .join(Hesap, Hesap.id == Kurum.hesap_id)
        .where(Kurum.dogrulama_durumu == durum)
        .order_by(Hesap.olusturma_tarihi.desc())
    )
    return [_firma_satiri(kurum, tarih) for kurum, tarih in satirlar.all()]


@router.post("/firmalar/{kurum_id}/dogrula", response_model=OnayBekleyenFirma)
async def firmayi_dogrula(
    kurum_id: uuid.UUID,
    istek: FirmaDogrulamaIstegi,
    _hesap: Hesap = Depends(rol_gerekli(ROL_GIRVAK)),
    oturum: AsyncSession = Depends(get_session),
) -> OnayBekleyenFirma:
    """GİRVAK'ın kararı: `dogrulandi` ya da `simdilik_degil`.

    Aynı kararın tekrarı 200 ve yan etkisiz. GİRVAK kararını değiştirebilir.
    Firmaya yalnızca doğrulanınca bildirim gider; "şimdilik değil" sessiz
    (olumsuz haber nazik: firma "Doğrulama bekleniyor" görmeye devam eder).
    """
    satir = (
        await oturum.execute(
            select(Kurum, Hesap.olusturma_tarihi)
            .join(Hesap, Hesap.id == Kurum.hesap_id)
            .where(Kurum.id == kurum_id)
            .with_for_update(of=Kurum)
        )
    ).first()
    if satir is None:
        raise bulunamadi(FIRMA_BULUNAMADI)
    kurum, kayit_tarihi = satir
    if kurum.dogrulama_durumu != istek.karar:
        kurum.dogrulama_durumu = istek.karar
        kurum.dogrulama_tarihi = dt.datetime.now(dt.UTC)
        if istek.karar == firma_dogrulama.DOGRULANDI:
            bildirim_ekle(oturum, kurum.hesap_id, TUR_FIRMA_DOGRULANDI, DOGRULANDI_METNI)
    await oturum.commit()
    return _firma_satiri(kurum, kayit_tarihi)
