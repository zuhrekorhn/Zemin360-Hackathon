"""Referans isteklerinin orkestrasyonu: isteme, yanıt, geri çekme, zaman aşımı,
hatırlatma, yeniden isteme (docs/dogrulama.md § 7).

Kurallar `app/agents/dogrulama/` (durum makinesi, form puanı, destek, geçerlilik);
burada modele uygulanmaları. Commit ve e-postanın gönderimi çağıranın işi: servis
gönderilecek e-postayı döner, uç yanıttan sonra arka planda gönderir (İ9).
Durum geçişinin bildirimi geçişi yapan fonksiyonda, aynı işlemde yazılır.
"""

from __future__ import annotations

import datetime as dt
import secrets
import uuid
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.dogrulama import (
    DURUM_BEKLIYOR,
    DURUM_GERI_CEKILDI,
    HATIRLATMA_GUN,
    OLAY_GERI_CEK,
    OLAY_YANIT,
    OLAY_ZAMAN_ASIMI,
    REFERANS_TIMEOUT_GUN,
    ZATEN_BEKLENIYOR,
    GecersizReferansGecisi,
    ReferansDestegi,
    ReferansYaniti,
    gecerli_referans_yanitlari,
    hatirlatma_zamani_mi,
    referans_basligi,
    referans_destegi,
    referans_gecerli_mi,
    referans_gecisi,
    referans_yeniden_istenebilir_mi,
    zaman_asimina_ugradi_mi,
)
from app.core.dis_servisler.eposta import Eposta
from app.core.istek_izi import IstekIzi
from app.models.bildirim import TUR_REFERANS_YANIT_YOK, TUR_REFERANS_YANITI
from app.models.guven_skoru import GuvenSkoru
from app.models.referans_istegi import ReferansIstegi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler.bildirim import bildirim_ekle
from app.servisler.dogrulama.isaretler import referans_suphesi
from app.servisler.dogrulama.referans_epostasi import (
    ReferansEpostaBaglami,
    hatirlatma_epostasi,
    istek_epostasi,
)
from app.servisler.dogrulama.sorgular import cikti_getir, gencin_adi, gencin_hesap_id


class ReferansYenidenIstenemez(Exception):
    """Yeniden isteme bu istek için anlamlı değil. Mesaj kullanıcıya gösterilir (409)."""


class KendiReferansi(ValueError):
    """Genç kendi adresini referans gösterdi (422)."""


class ReferansZatenBekliyor(Exception):
    """Aynı kalemde aynı kişiden bekleyen istek var (409)."""


KENDI_REFERANSI = "Kendi e-posta adresini referans olarak gösteremezsin."
YANIT_YOK_BILDIRIMI = (
    "Bir referans isteğin süresinde yanıtlanmadı. Bu olumsuz bir işaret değil; "
    "istersen yeniden isteyebilir ya da başka birinden referans isteyebilirsin."
)
YANIT_BILDIRIMI = "Bir referansın yanıt verdi; güven göstergen güncellendi."


def _ayni_adres(a: str, b: str) -> bool:
    return a.strip().casefold() == b.strip().casefold()


def _simdi() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


# --- Puan ve destek ------------------------------------------------------------------------


def referans_guncel_mi(cikti: SomutCikti, referans: ReferansIstegi) -> bool:
    """Bu referans yanıtı iş kaleminin güncel hâli için mi? (docs/kararlar.md G8)"""
    return referans_gecerli_mi(referans.yanit_tarihi, cikti.icerik_tarihi)


def _yanit(r: ReferansIstegi) -> ReferansYaniti:
    return ReferansYaniti(
        puan=r.puan,
        yanit_tarihi=r.yanit_tarihi,
        iddia=r.iddia_dogru,
        pay=r.pay_dogru,
        sonuc=r.sonuc_dogru,
    )


def _guncel_yanitlar(cikti: SomutCikti) -> list[ReferansYaniti]:
    return gecerli_referans_yanitlari(map(_yanit, cikti.referans_istekleri), cikti.icerik_tarihi)


def ucuncu_taraf_puani(cikti: SomutCikti) -> int | None:
    """Referans başlığı, yalnızca güncel yanıtlardan; yoksa None ("—").

    `cikti.referans_istekleri` yüklenmiş olmalı.
    """
    return referans_basligi(_guncel_yanitlar(cikti))


def referans_destegi_hesapla(cikti: SomutCikti) -> ReferansDestegi:
    """Sonuç ve Rol için referans desteği (güncel yanıtlarda "evet")."""
    return referans_destegi(_guncel_yanitlar(cikti))


# --- Zaman aşımı ve hatırlatma -------------------------------------------------------------


async def _gence_bildir(
    oturum: AsyncSession, somut_cikti_id: uuid.UUID, tur: str, metin: str
) -> None:
    kart_id = await oturum.scalar(
        select(SomutCikti.yetenek_karti_id).where(SomutCikti.id == somut_cikti_id)
    )
    if kart_id is not None:
        bildirim_ekle(oturum, await gencin_hesap_id(oturum, kart_id), tur, metin)


async def zaman_asimini_isle(
    oturum: AsyncSession, referans: ReferansIstegi, simdi: dt.datetime | None = None
) -> bool:
    """Süresi dolmuşsa `yanit_yok`'a geçirir ve gence bildirir; değişiklik varsa True.

    Zamanlayıcı yok (bilinçli): geçiş, kayda her dokunulduğunda ve Canlılık
    taramasında hesaplanıyor; hangisi önce gelirse bildirimi o yazar (bir kez).
    """
    if not zaman_asimina_ugradi_mi(referans.olusturma_tarihi, referans.durum, simdi):
        return False
    referans.durum = referans_gecisi(referans.durum, OLAY_ZAMAN_ASIMI)
    await _gence_bildir(
        oturum, referans.somut_cikti_id, TUR_REFERANS_YANIT_YOK, YANIT_YOK_BILDIRIMI
    )
    return True


async def zaman_asimlarini_isle(
    oturum: AsyncSession, referanslar: Iterable[ReferansIstegi], simdi: dt.datetime | None = None
) -> bool:
    """Birden çok istek için `zaman_asimini_isle`; herhangi biri geçtiyse True."""
    degisti = False
    for referans in list(referanslar):
        degisti = await zaman_asimini_isle(oturum, referans, simdi) or degisti
    return degisti


@dataclass(frozen=True)
class ReferansTaramasi:
    hatirlatmalar: list[Eposta]
    zaman_asimi: int


async def referans_taramasi(
    oturum: AsyncSession, simdi: dt.datetime | None = None
) -> ReferansTaramasi:
    """Canlılık taramasının referans kısmı: 3. gün tek hatırlatma, 7. gün "yanıt yok".

    Hatırlatma yalnızca sistemin e-posta gönderdiği isteklere gider (sistem e-postasından
    önce açılanların linki gence verilmişti). E-postalar döner; tarama commit'ten
    sonra gönderir.
    """
    simdi = simdi or _simdi()
    bekleyenler = await oturum.scalars(
        select(ReferansIstegi)
        .options(
            selectinload(ReferansIstegi.somut_cikti)
            .selectinload(SomutCikti.yetenek_karti)
            .selectinload(YetenekKarti.kullanici)
        )
        .where(
            ReferansIstegi.durum == DURUM_BEKLIYOR,
            ReferansIstegi.olusturma_tarihi <= simdi - dt.timedelta(days=HATIRLATMA_GUN),
        )
    )
    hatirlatmalar: list[Eposta] = []
    zaman_asimi = 0
    for referans in list(bekleyenler):
        if await zaman_asimini_isle(oturum, referans, simdi):
            zaman_asimi += 1
            continue
        if referans.gonderim_tarihi is None or not hatirlatma_zamani_mi(
            referans.olusturma_tarihi, referans.durum, referans.hatirlatma_tarihi, simdi
        ):
            continue
        referans.hatirlatma_tarihi = simdi
        cikti = referans.somut_cikti
        gecen = (simdi - referans.olusturma_tarihi).days
        hatirlatmalar.append(
            hatirlatma_epostasi(
                ReferansEpostaBaglami(
                    alici=referans.referans_email,
                    token=referans.token,
                    genc_adi=cikti.yetenek_karti.kullanici.ad,
                    baslik=cikti.baslik,
                ),
                kalan_gun=max(REFERANS_TIMEOUT_GUN - gecen, 1),
            )
        )
    return ReferansTaramasi(hatirlatmalar=hatirlatmalar, zaman_asimi=zaman_asimi)


# --- Yanıt ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class FormYaniti:
    """Referansın 4 soruluk yanıtı. Kalemde yazılmamış pay / sonuç sorulmaz (None)."""

    iliski: str
    iddia: str
    pay: str | None = None
    sonuc: str | None = None
    yorum: str | None = None


@dataclass(frozen=True)
class YanitSonucu:
    cikti: SomutCikti
    # Sonuç ya da Rol desteği değişti: kalem yeniden puanlanmalı (arka planda).
    destek_degisti: bool


async def referans_yanitla(
    oturum: AsyncSession,
    referans: ReferansIstegi,
    yanit: FormYaniti,
    yanit_izi: IstekIzi | None = None,
) -> YanitSonucu:
    """Yanıtı koşullu güncellemeyle yazar, Referans başlığını günceller, gence bildirir.

    İki sekmeden aynı anda gelen yanıtın yalnızca biri kaydedilir:
    `UPDATE … WHERE durum = 'bekliyor' RETURNING id`. Geçersiz geçişte
    (yanıtlanmış, süresi dolmuş, geri çekilmiş) `GecersizReferansGecisi`. Zaman
    aşımını çağıran önce işler: GET ve POST aynı kuralı uygulasın diye.
    Yanıtın şüphe sinyalleri (`referans_supheli`) aynı işlemde yazılır; puanı
    değiştirmez (İ1).
    """
    hedef = referans_gecisi(referans.durum, OLAY_YANIT)
    cikti = await cikti_getir(oturum, referans.somut_cikti_id)
    onceki_destek = referans_destegi_hesapla(cikti)
    simdi = _simdi()
    degerler = {
        "durum": hedef,
        "iliski": yanit.iliski,
        "iddia_dogru": yanit.iddia,
        # Kalemde yazılmamış bir şey sorulmadı; gelen değer yok sayılır.
        "pay_dogru": yanit.pay if cikti.kendi_rolu else None,
        "sonuc_dogru": yanit.sonuc if cikti.olculebilir_sonuc else None,
        "yanit_metni": yanit.yorum,
        "yanit_tarihi": simdi,
    }
    kaydedilen = await oturum.scalar(
        update(ReferansIstegi)
        .where(ReferansIstegi.id == referans.id, ReferansIstegi.durum == DURUM_BEKLIYOR)
        .values(**degerler)
        .returning(ReferansIstegi.id)
        .execution_options(synchronize_session=False)
    )
    if kaydedilen is None:
        # Arada başka bir yanıt kaydedildi.
        raise GecersizReferansGecisi(hedef, OLAY_YANIT)
    for alan, deger in degerler.items():
        setattr(referans, alan, deger)
    await referans_suphesi.yanit_sinyalleri(oturum, referans, cikti, yanit_izi, simdi)

    if cikti.guven_skoru is None:
        # Kanıt değerlendirilmeden referans gelirse yalnızca Referans başlığı
        # dolar; Kanıt, Sonuç ve Rol "—" kalır.
        cikti.guven_skoru = GuvenSkoru()
    # Birden fazla referans yanıtlamış olabilir; son gelen öncekini ezmesin.
    cikti.guven_skoru.ucuncu_taraf_onayi = ucuncu_taraf_puani(cikti)
    bildirim_ekle(
        oturum,
        await gencin_hesap_id(oturum, cikti.yetenek_karti_id),
        TUR_REFERANS_YANITI,
        YANIT_BILDIRIMI,
    )
    return YanitSonucu(cikti, referans_destegi_hesapla(cikti) != onceki_destek)


# --- İsteme, geri çekme, yeniden isteme ------------------------------------------------------


def _yeni_istek(
    cikti: SomutCikti, referans_email: str, istek_izi: IstekIzi | None = None
) -> ReferansIstegi:
    # Token burada üretiliyor: e-posta flush'tan önce kuruluyor.
    istek = ReferansIstegi(
        referans_email=referans_email.strip(),
        token=secrets.token_urlsafe(32),
        gonderim_tarihi=_simdi(),
    )
    # İsteyen gencin izi: referansın yanıtıyla karşılaştırılır (referans_supheli).
    referans_suphesi.istek_izi_yaz(istek, istek_izi)
    cikti.referans_istekleri.append(istek)
    return istek


def isteme_engeli(cikti: SomutCikti, referans_email: str, gencin_epostasi: str | None) -> None:
    """Engeller (§ 7): gencin kendi adresi (422), aynı kişiden bekleyen istek (409).

    `cikti.referans_istekleri` yüklenmiş olmalı.
    """
    if gencin_epostasi and _ayni_adres(referans_email, gencin_epostasi):
        raise KendiReferansi(KENDI_REFERANSI)
    if any(
        r.durum == DURUM_BEKLIYOR and _ayni_adres(r.referans_email, referans_email)
        for r in cikti.referans_istekleri
    ):
        raise ReferansZatenBekliyor(ZATEN_BEKLENIYOR)


async def istek_epostasi_kur(
    oturum: AsyncSession, cikti: SomutCikti, istek: ReferansIstegi
) -> Eposta:
    """İsteğin e-postası; uç yanıttan sonra gönderir."""
    ad = await gencin_adi(oturum, cikti.yetenek_karti_id)
    return istek_epostasi_hazirla(istek, cikti.baslik, ad)


def istek_epostasi_hazirla(istek: ReferansIstegi, baslik: str, genc_adi: str | None) -> Eposta:
    """Gencin adı elde olduğunda (ör. kart henüz kaydedilmeden) e-posta."""
    return istek_epostasi(
        ReferansEpostaBaglami(
            alici=istek.referans_email,
            token=istek.token,
            genc_adi=genc_adi or "Bir Zemin360 kullanıcısı",
            baslik=baslik,
        ),
        gecerlilik_gun=REFERANS_TIMEOUT_GUN,
    )


def yeni_istek_ac(
    cikti: SomutCikti,
    referans_email: str,
    gencin_epostasi: str | None,
    istek_izi: IstekIzi | None = None,
) -> ReferansIstegi:
    """Engelleri uygular ve isteği açar (e-postası `istek_epostasi_kur` ile kurulur).

    Göstergeye dokunmaz, model çağrılmaz.
    """
    isteme_engeli(cikti, referans_email, gencin_epostasi)
    return _yeni_istek(cikti, referans_email, istek_izi)


async def referans_iste(
    oturum: AsyncSession,
    cikti: SomutCikti,
    referans_email: str,
    gencin_epostasi: str | None,
    istek_izi: IstekIzi | None = None,
) -> Eposta:
    """Yeni referans isteği açar ve gönderilecek e-postayı döner."""
    await zaman_asimlarini_isle(oturum, cikti.referans_istekleri)
    istek = yeni_istek_ac(cikti, referans_email, gencin_epostasi, istek_izi)
    return await istek_epostasi_kur(oturum, cikti, istek)


async def referansi_geri_cek(oturum: AsyncSession, referans: ReferansIstegi) -> None:
    """Bekleyen isteği geri çeker (ör. yanlış adres). Tekrarı yan etkisiz; yanıtlanmış
    ya da süresi dolmuş istek için `GecersizReferansGecisi` (409)."""
    await zaman_asimini_isle(oturum, referans)
    if referans.durum == DURUM_GERI_CEKILDI:
        return
    referans.durum = referans_gecisi(referans.durum, OLAY_GERI_CEK)


def yeniden_isteme_engeli(cikti: SomutCikti, referans: ReferansIstegi) -> str | None:
    """Bu istek yeniden istenebilir mi? Değilse nedeni (kural:
    `referans_yeniden_istenebilir_mi`). Uç ve arayüz düğmesi aynı yanıtı kullanır."""
    return referans_yeniden_istenebilir_mi(
        durum=referans.durum,
        guncel=referans_guncel_mi(cikti, referans),
        ayni_kisiden_bekleyen_var=any(
            r.id != referans.id
            and _ayni_adres(r.referans_email, referans.referans_email)
            and r.durum == DURUM_BEKLIYOR
            for r in cikti.referans_istekleri
        ),
    )


async def referansi_yeniden_iste(
    oturum: AsyncSession,
    cikti: SomutCikti,
    referans: ReferansIstegi,
    istek_izi: IstekIzi | None = None,
) -> Eposta:
    """Aynı kişiye yeni istek (yeni token, yeni e-posta); eski yanıt geçmiş olarak kalır.

    Anlamlı değilse `ReferansYenidenIstenemez`. Değerlendirme yeniden çalışmaz.
    """
    await zaman_asimini_isle(oturum, referans)
    engel = yeniden_isteme_engeli(cikti, referans)
    if engel:
        raise ReferansYenidenIstenemez(engel)
    yeni = _yeni_istek(cikti, referans.referans_email, istek_izi)
    return await istek_epostasi_kur(oturum, cikti, yeni)
