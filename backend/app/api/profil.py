"""Genç ve firma profili: kayıt formu alanları, profil düzenleme ve kart onayıyla gelen güncelleme.

- `GET /kurum/profil`, `PATCH /kurum/profil` (firma, yalnızca kendisi):
  docs/plans/firma-akisi.md § 2. Gençteki kurallar: yalnızca gönderilen alan
  değişir, zorunlu alan boşaltılamaz.

- `GET /profil`, `PATCH /profil` (genç, yalnızca kendisi): kayıt formundaki
  alanlar (docs/plans/genc-akisi.md § 6.1). Yalnızca gönderilen alan değişir.
- Kart onayıyla gelen güncelleme (docs/faz-b-kimlik-ve-dongu.md § 4): onay
  yalnızca eşleştirmeyi etkileyen alanları günceller. Kural (Faz A'dan): boş
  gelen alan kayıtlı değeri SİLMEZ. İkinci kartını onaylayan genç şehrini ya da
  müsaitliğini yeniden yazmak zorunda değil.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dogrulama.kimlik import ad_kilitli
from app.agents.kart_duzenleme import degisen_alanlar, yeniden_eslestirme_gerekir_mi
from app.api.kimlik import rol_gerekli
from app.core import calisma_modeli, firma_dogrulama, firma_profili
from app.core.alan_adlari import FIRMA_ALAN_ADLARI, GENC_ALAN_ADLARI, bos_alan_mesaji
from app.core.genc_profili import ZORUNLU_ALANLAR, eksik_profil_alanlari
from app.core.sehir import sehir_kanonik
from app.db.session import get_session
from app.models.hesap import ROL_GENC, ROL_KURUM, Hesap
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.models.yetenek_karti import YetenekKarti
from app.schemas.kesif import GencProfili
from app.schemas.profil import (
    AdDegisikligiIstegi,
    FirmaProfilGuncelleme,
    FirmaProfilYaniti,
    GencProfilGuncelleme,
    GencProfilYaniti,
)
from app.schemas.tanimlama import KurumProfili
from app.servisler import firma_karti as firma_karti_servisi
from app.servisler import kart_hazirlama, kimlik_dogrulama

router = APIRouter(tags=["profil"])

# Profile yazılabilen alanlar (şemadaki adlarla birebir). `kvkk_onay` hesaba
# yazılır, burada değil.
PROFIL_ALANLARI: tuple[str, ...] = (
    "ad",
    "sehir",
    "calisma_modelleri",
    "kariyer_durumu",
    "musaitlikler",
    "musaitlik_baslangici",
    "okul",
    "bolum",
    "sinif",
    "mezuniyet_yili",
    "github_url",
    "linkedin_url",
    "portfolyo_url",
)
# Boşaltılamayan alanlar: zorunlu profil alanları ve ad.
BOSALTILAMAZ = frozenset({"ad", *ZORUNLU_ALANLAR})


def profili_uygula(kullanici: Kullanici, degerler: dict[str, Any]) -> None:
    """Doğrulanmış değerleri profile yazar (kayıt ve PATCH aynı yoldan)."""
    for alan, deger in degerler.items():
        if alan in PROFIL_ALANLARI:
            setattr(kullanici, alan, list(deger) if isinstance(deger, list | tuple) else deger)


def profilin_eksikleri(kullanici: Kullanici) -> list[str]:
    return eksik_profil_alanlari(
        sehir=kullanici.sehir,
        calisma_modelleri=kullanici.calisma_modelleri,
        musaitlikler=kullanici.musaitlikler,
        kariyer_durumu=kullanici.kariyer_durumu,
    )


def bosaltilan_zorunlular(gonderilenler: dict[str, Any]) -> list[str]:
    """PATCH'te boş gönderilmiş zorunlu alanlar (sabit sırada)."""
    return sorted(
        alan for alan, deger in gonderilenler.items() if alan in BOSALTILAMAZ and not deger
    )


def profil_yaniti(
    hesap: Hesap, kullanici: Kullanici, bekleyen_ad: str | None = None
) -> GencProfilYaniti:
    return GencProfilYaniti(
        ad=kullanici.ad,
        email=kullanici.email,
        sehir=kullanici.sehir,
        calisma_modelleri=list(kullanici.calisma_modelleri or []),
        kariyer_durumu=kullanici.kariyer_durumu,
        musaitlikler=list(kullanici.musaitlikler or []),
        musaitlik_baslangici=kullanici.musaitlik_baslangici,
        okul=kullanici.okul,
        bolum=kullanici.bolum,
        sinif=kullanici.sinif,
        mezuniyet_yili=kullanici.mezuniyet_yili,
        github_url=kullanici.github_url,
        linkedin_url=kullanici.linkedin_url,
        portfolyo_url=kullanici.portfolyo_url,
        kvkk_onay_tarihi=hesap.kvkk_onay_tarihi,
        eksik_alanlar=profilin_eksikleri(kullanici),
        ad_kilitli=ad_kilitli(hesap.eposta_dogrulandi_tarihi),
        bekleyen_ad=bekleyen_ad,
    )


@router.get("/profil", response_model=GencProfilYaniti)
async def profil_getir(
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)), oturum: AsyncSession = Depends(get_session)
) -> GencProfilYaniti:
    bekleyen = await kimlik_dogrulama.bekleyen_ad_talebi(oturum, hesap.kullanici.id)
    return profil_yaniti(hesap, hesap.kullanici, bekleyen)


@router.patch("/profil", response_model=GencProfilYaniti)
async def profil_guncelle(
    istek: GencProfilGuncelleme,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> GencProfilYaniti:
    """Yalnızca gönderilen alan değişir; zorunlu alan boşaltılamaz (422).

    Başkasının profili diye bir yol yok: profil token'daki hesabın profili.

    Filtre alanı (şehir, çalışma modeli, müsaitlik) değiştiyse gencin kartları
    yanıttan sonra yeniden eşleşir; doğrulama gerekmez, kart versiyonu artmaz.
    """
    gonderilenler = {alan: getattr(istek, alan) for alan in istek.model_fields_set}
    bosalanlar = bosaltilan_zorunlular(gonderilenler)
    if bosalanlar:
        raise HTTPException(
            status_code=422, detail=bos_alan_mesaji(bosalanlar, GENC_ALAN_ADLARI, siz=False)
        )
    if "ad" in gonderilenler and not kimlik_dogrulama.profilden_ad_degisebilir_mi(
        hesap, gonderilenler["ad"]
    ):
        raise HTTPException(status_code=409, detail=kimlik_dogrulama.AD_KILITLI)
    kullanici = hesap.kullanici
    oncesi = {alan: getattr(kullanici, alan) for alan in PROFIL_ALANLARI}
    degisenler = degisen_alanlar(
        oncesi, {a: d for a, d in gonderilenler.items() if a in PROFIL_ALANLARI}
    )
    profili_uygula(kullanici, gonderilenler)
    if gonderilenler.get("kvkk_onay") and hesap.kvkk_onay_tarihi is None:
        hesap.kvkk_onay_tarihi = dt.datetime.now(dt.UTC)
    await oturum.commit()
    if yeniden_eslestirme_gerekir_mi(degisenler):
        kartlar = await oturum.execute(
            select(YetenekKarti.id, YetenekKarti.versiyon).where(
                YetenekKarti.kullanici_id == kullanici.id
            )
        )
        for kart_id, versiyon in kartlar.all():
            arka_plan.add_task(kart_hazirlama.karti_hazirla, kart_id, versiyon)
    bekleyen = await kimlik_dogrulama.bekleyen_ad_talebi(oturum, kullanici.id)
    return profil_yaniti(hesap, kullanici, bekleyen)


@router.post("/profil/ad-degisikligi", response_model=GencProfilYaniti, status_code=202)
async def ad_degisikligi_iste(
    istek: AdDegisikligiIstegi,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC)),
    oturum: AsyncSession = Depends(get_session),
) -> GencProfilYaniti:
    """Kilitli ad için GİRVAK'a talep (plan § 6.3). Ad onaya kadar değişmez.

    Ad kilitli değilse ya da bekleyen talep varsa 409, aynı ad 422.
    """
    try:
        await kimlik_dogrulama.ad_degisikligi_iste(oturum, hesap, istek.yeni_ad, istek.gerekce)
    except (kimlik_dogrulama.AdKilitliDegil, kimlik_dogrulama.BekleyenTalepVar) as hata:
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    except kimlik_dogrulama.AyniAd as hata:
        raise HTTPException(status_code=422, detail=str(hata)) from hata
    await oturum.commit()
    return profil_yaniti(hesap, hesap.kullanici, istek.yeni_ad)


def gencin_profilini_guncelle(kullanici: Kullanici, profil: GencProfili) -> None:
    sehir = sehir_kanonik(profil.sehir)
    if sehir:
        kullanici.sehir = sehir
    modeller = calisma_modeli.temizle(profil.calisma_modelleri)
    if modeller:
        kullanici.calisma_modelleri = modeller
    if profil.musaitlikler:
        kullanici.musaitlikler = list(profil.musaitlikler)


# --- Firma profili (docs/plans/firma-akisi.md § 2) ---------------------------------------

FIRMA_PROFIL_ALANLARI: tuple[str, ...] = (
    "ad",
    "tur",
    "sektor",
    "sehir",
    "web_sitesi",
    "calisan_araligi",
    "kurulus_yili",
    "tanitim",
    "yetkili_ad",
    "yetkili_gorev",
)
FIRMA_BOSALTILAMAZ = frozenset({"ad", *firma_profili.ZORUNLU_ALANLAR})


def firma_profilini_uygula(kurum: Kurum, degerler: dict[str, Any]) -> None:
    """Doğrulanmış değerleri firma profiline yazar (kayıt ve PATCH aynı yoldan)."""
    for alan, deger in degerler.items():
        if alan in FIRMA_PROFIL_ALANLARI:
            setattr(kurum, alan, deger)


def firmanin_eksikleri(kurum: Kurum) -> list[str]:
    return firma_profili.eksik_firma_alanlari(tur=kurum.tur, sektor=kurum.sektor, sehir=kurum.sehir)


def firma_profil_yaniti(hesap: Hesap, kurum: Kurum) -> FirmaProfilYaniti:
    return FirmaProfilYaniti(
        ad=kurum.ad,
        email=kurum.iletisim_email,
        tur=kurum.tur,
        sektor=kurum.sektor,
        sehir=kurum.sehir,
        web_sitesi=kurum.web_sitesi,
        calisan_araligi=kurum.calisan_araligi,
        kurulus_yili=kurum.kurulus_yili,
        tanitim=kurum.tanitim,
        yetkili_ad=kurum.yetkili_ad,
        yetkili_gorev=kurum.yetkili_gorev,
        kvkk_onay_tarihi=hesap.kvkk_onay_tarihi,
        eksik_alanlar=firmanin_eksikleri(kurum),
        dogrulandi=kurum.dogrulama_durumu == firma_dogrulama.DOGRULANDI,
    )


@router.get("/kurum/profil", response_model=FirmaProfilYaniti)
async def firma_profili_getir(
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
) -> FirmaProfilYaniti:
    return firma_profil_yaniti(hesap, hesap.kurum)


@router.patch("/kurum/profil", response_model=FirmaProfilYaniti)
async def firma_profili_guncelle(
    istek: FirmaProfilGuncelleme,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> FirmaProfilYaniti:
    """Yalnızca gönderilen alan değişir; zorunlu alan boşaltılamaz (422).

    Profil token'daki hesabın firması; başkasının profili diye bir yol yok.

    Eşleştirmeyi etkileyen alan gerçekten değiştiyse, kartı olan firma için iş
    yanıttan sonra arka planda yürür: sektör kartın embedding'ini ve önerilerini
    yeniler; şehir ya da tür, firmanın aday olduğu açık ortak ilanlarını yeniden
    eşleştirir. Aynı değerle kaydetme hiçbir şeyi tetiklemez.
    """
    gonderilenler = {alan: getattr(istek, alan) for alan in istek.model_fields_set}
    bosalanlar = sorted(
        alan for alan, deger in gonderilenler.items() if alan in FIRMA_BOSALTILAMAZ and not deger
    )
    if bosalanlar:
        raise HTTPException(
            status_code=422, detail=bos_alan_mesaji(bosalanlar, FIRMA_ALAN_ADLARI, siz=True)
        )
    kurum = hesap.kurum
    if "web_sitesi" in gonderilenler and firma_dogrulama.dogrulama_sifirlanir_mi(
        kurum.web_sitesi, gonderilenler["web_sitesi"]
    ):
        # Doğrulama kimlikle ilgili: site değişince GİRVAK yeniden bakar (karar 15).
        kurum.dogrulama_durumu = firma_dogrulama.BEKLIYOR
        kurum.dogrulama_tarihi = None
    degisenler = degisen_alanlar(
        {alan: getattr(kurum, alan) for alan in FIRMA_PROFIL_ALANLARI},
        {a: d for a, d in gonderilenler.items() if a in FIRMA_PROFIL_ALANLARI},
    )
    firma_profilini_uygula(kurum, gonderilenler)
    if gonderilenler.get("kvkk_onay") and hesap.kvkk_onay_tarihi is None:
        hesap.kvkk_onay_tarihi = dt.datetime.now(dt.UTC)
    kurum_id = kurum.id
    sektor = firma_profili.sektor_degisti_mi(degisenler)
    kesin_sart = firma_profili.kesin_sart_degisti_mi(degisenler)
    arka_is = None
    if sektor or kesin_sart:
        kart = await firma_karti_servisi.kurumun_karti(oturum, kurum_id, kilitle=True)
        if kart is not None:
            if sektor:
                # Sektör kartın temsil metninde ve gerekçe isteminde: eski kararlar
                # yeni bilgiye dayanmaz (kart düzenlemesindeki kural).
                await firma_karti_servisi.onerilerin_gerekcesini_bosalt(oturum, kart.id)
                arka_is = (firma_karti_servisi.firma_kartini_hazirla, kart.id, kart.versiyon)
            else:
                arka_is = (firma_karti_servisi.firma_kartini_yeniden_eslestir, kart.id)
    await oturum.commit()
    if arka_is is not None:
        arka_plan.add_task(*arka_is)
    return firma_profil_yaniti(hesap, hesap.kurum)


def kurumun_profilini_guncelle(kurum: Kurum, profil: KurumProfili) -> None:
    sektor = (profil.sektor or "").strip()
    if sektor:
        kurum.sektor = sektor
    sehir = sehir_kanonik(profil.sehir)
    if sehir:
        kurum.sehir = sehir
