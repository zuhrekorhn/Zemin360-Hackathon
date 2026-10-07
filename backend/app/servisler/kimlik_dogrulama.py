"""Kayıt e-postasının doğrulanması ve ad kilidi (docs/dogrulama.md § 6.3,
bulgular 37 ve 48).

Akış: kayıt → `baglanti_olustur` (aynı istekte) → e-posta yanıttan sonra gider
(`epostayi_gonder`, arka plan; hatası kaydı düşürmez) → kullanıcı bağlantıyı
açar → `dogrula`. Doğrulama girişi ya da başka bir akışı engellemez; tek etkisi
gencin adını kilitlemek ve ada dayalı seviye A koşulunu açmaktır.

Ad kilidi: e-posta doğrulanınca gencin adı profilden değişmez; değişiklik
GİRVAK'a talep olarak gider (`ad_degisikligi_iste`, işaret `ad_degisikligi`).
Onaylanırsa `AdDegisikligiIsleyici` adı uygular ve adla sahipliği kurulmuş
kanıtların kalemlerini yeniden değerlendirmeye açar.

Sözleşme (diğer servislerle aynı): model değişir, commit ve HTTP'ye çeviri
çağıranın işidir.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import secrets
import uuid
from urllib.parse import quote

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dogrulama.kimlik import ad_kilitli, ad_parcalari
from app.agents.inceleme_durumu import ACIK, KAPANDI
from app.core.config import get_settings
from app.core.dis_servisler import Eposta, dusmeden_gonder, kurulum
from app.core.kanit_okuma.belge import SahiplikKaynagi
from app.models.bildirim import TUR_AD_DEGISIKLIGI_SONUCU
from app.models.eposta_dogrulama import EpostaDogrulama
from app.models.guven_skoru import GuvenSkoru
from app.models.hesap import ROL_KURUM, Hesap
from app.models.inceleme_isareti import TUR_AD_DEGISIKLIGI, IncelemeIsareti
from app.models.kanit_parcasi import KanitParcasi
from app.models.kullanici import Kullanici
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.servisler import inceleme, kart_hazirlama

GECERLILIK = dt.timedelta(hours=24)
# Yeni bağlantı isteği bundan sık olamaz (art arda tıklama e-posta yağdırmasın).
YENIDEN_GONDERME_ARALIGI = dt.timedelta(minutes=1)


class BaglantiGecersiz(Exception):
    """Bağlantı yok ya da süresi dolmuş. Mesaj kullanıcıya gösterilir."""


class ZatenDogrulandi(Exception):
    """Hesabın e-postası zaten doğrulanmış (yeniden gönderme isteği)."""


class CokSikIstek(Exception):
    """Yeni bağlantı için biraz beklenmeli. Mesaj kullanıcıya gösterilir."""


def _ozet(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _simdi() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def dogrulandi_mi(hesap: Hesap) -> bool:
    return hesap.eposta_dogrulandi_tarihi is not None


async def baglanti_olustur(oturum: AsyncSession, hesap: Hesap) -> str:
    """Yeni bağlantının token'ını döner; hesabın eski bağlantıları geçersiz olur."""
    await oturum.execute(delete(EpostaDogrulama).where(EpostaDogrulama.hesap_id == hesap.id))
    token = secrets.token_urlsafe(32)
    oturum.add(
        EpostaDogrulama(
            hesap_id=hesap.id, token_ozeti=_ozet(token), son_gecerlilik=_simdi() + GECERLILIK
        )
    )
    return token


async def yeniden_baglanti_olustur(oturum: AsyncSession, hesap: Hesap) -> str:
    if dogrulandi_mi(hesap):
        raise ZatenDogrulandi
    son = await oturum.scalar(
        select(EpostaDogrulama.olusturma_tarihi)
        .where(EpostaDogrulama.hesap_id == hesap.id)
        .order_by(EpostaDogrulama.olusturma_tarihi.desc())
        .limit(1)
    )
    if son is not None and _simdi() - son < YENIDEN_GONDERME_ARALIGI:
        raise CokSikIstek("Bağlantı az önce gönderildi. Bir dakika sonra yeniden deneyebilirsin.")
    return await baglanti_olustur(oturum, hesap)


async def dogrula(oturum: AsyncSession, token: str) -> Hesap:
    """Bağlantı geçerliyse hesabı doğrular. Aynı bağlantının tekrarı yan etkisiz."""
    kayit = await oturum.scalar(
        select(EpostaDogrulama).where(EpostaDogrulama.token_ozeti == _ozet(token))
    )
    if kayit is None or kayit.son_gecerlilik <= _simdi():
        raise BaglantiGecersiz(
            "Bu bağlantı geçersiz ya da süresi dolmuş. Giriş yapıp yeni bağlantı isteyebilirsin."
        )
    hesap = await oturum.get(Hesap, kayit.hesap_id, with_for_update=True)
    if hesap.eposta_dogrulandi_tarihi is None:
        hesap.eposta_dogrulandi_tarihi = _simdi()
    return hesap


async def dogrulama_sonrasi_kart(oturum: AsyncSession, hesap: Hesap) -> uuid.UUID | None:
    """E-posta doğrulanınca kimlik koşulu değişir: çapalı dosyası olan gencin kalemleri
    yeniden okunmalı (dosya seviyesi okuma anında kimlikle hesaplanır, docs/dogrulama.md § 6.3).
    Döner: yeniden okunacak kart; yoksa None."""
    return await oturum.scalar(
        select(YetenekKarti.id)
        .join(Kullanici, Kullanici.id == YetenekKarti.kullanici_id)
        .join(SomutCikti, SomutCikti.yetenek_karti_id == YetenekKarti.id)
        .join(KanitParcasi, KanitParcasi.somut_cikti_id == SomutCikti.id)
        .where(Kullanici.hesap_id == hesap.id, KanitParcasi.dosya_anahtari.is_not(None))
        .limit(1)
    )


def dogrulama_epostasi(hesap: Hesap, token: str) -> Eposta:
    """Hitap rehbere göre: firmaya "siz", gence "sen" (docs/icerik-rehberi.md)."""
    baglanti = f"{get_settings().uygulama_adresi.rstrip('/')}/eposta-dogrula?token={quote(token)}"
    if hesap.rol == ROL_KURUM:
        konu = "Zemin360: e-posta adresinizi doğrulayın"
        metin = (
            "Merhaba,\n\n"
            "Zemin360 hesabınızın e-posta adresini doğrulamak için bu bağlantıyı açın:\n"
            f"{baglanti}\n\n"
            "Bağlantı 24 saat geçerli. Bu hesabı siz açmadıysanız bu e-postayı yok sayabilirsiniz."
        )
    else:
        konu = "Zemin360: e-posta adresini doğrula"
        metin = (
            "Merhaba,\n\n"
            "Zemin360 hesabının e-posta adresini doğrulamak için bu bağlantıyı aç:\n"
            f"{baglanti}\n\n"
            "Bağlantı 24 saat geçerli. Bu hesabı sen açmadıysan bu e-postayı yok sayabilirsin."
        )
    return Eposta(alici=hesap.email, konu=konu, metin=metin)


async def epostayi_gonder(eposta: Eposta) -> None:
    """Arka plan işi: yanıttan sonra gönderir; hata kaydı ya da isteği düşürmez (İ9)."""
    await dusmeden_gonder(kurulum.eposta_gonderici(), eposta)


# --- Ad kilidi ve değişiklik talebi (docs/dogrulama.md § 6.3)
# -------------------------------------------

AD_KILITLI = (
    "E-postanı doğruladığın için adın kilitli. Değiştirmek için ad değişikliği "
    "talebi gönderebilirsin; GİRVAK inceleyip sonucu sana bildirir."
)


class AdKilitliDegil(Exception):
    """Ad kilitli değil; profilden değiştirilir (uçta 409)."""


class AyniAd(Exception):
    """İstenen ad bugünküyle aynı (uçta 422)."""


class BekleyenTalepVar(Exception):
    """Açık bir ad değişikliği talebi zaten var (uçta 409)."""


def ad_degisiyor_mu(eski: str | None, yeni: str | None) -> bool:
    """Yalnızca boşluk ya da büyük/küçük harf farkı değişiklik sayılmaz."""
    return ad_parcalari(eski or "") != ad_parcalari(yeni or "")


def profilden_ad_degisebilir_mi(hesap: Hesap, yeni_ad: str | None) -> bool:
    return not ad_kilitli(hesap.eposta_dogrulandi_tarihi) or not ad_degisiyor_mu(
        hesap.kullanici.ad, yeni_ad
    )


async def bekleyen_ad_talebi(oturum: AsyncSession, kullanici_id) -> str | None:
    isaret = await oturum.scalar(
        select(IncelemeIsareti).where(
            IncelemeIsareti.tur == TUR_AD_DEGISIKLIGI,
            IncelemeIsareti.kullanici_id == kullanici_id,
            IncelemeIsareti.durum == ACIK,
        )
    )
    return isaret.ayrinti.get("yeni_ad") if isaret is not None else None


async def ad_degisikligi_iste(
    oturum: AsyncSession, hesap: Hesap, yeni_ad: str, gerekce: str | None
) -> IncelemeIsareti:
    kullanici = hesap.kullanici
    if not ad_kilitli(hesap.eposta_dogrulandi_tarihi):
        raise AdKilitliDegil("Adın kilitli değil; profilinden değiştirebilirsin.")
    if not ad_degisiyor_mu(kullanici.ad, yeni_ad):
        raise AyniAd("Yeni ad bugünkü adınla aynı.")
    isaret, yeni_mi = await inceleme.isaret_ac(
        oturum,
        TUR_AD_DEGISIKLIGI,
        kullanici.id,
        ayrinti={"eski_ad": kullanici.ad, "yeni_ad": yeni_ad, "gerekce": gerekce},
    )
    if not yeni_mi:
        raise BekleyenTalepVar(
            "Bekleyen bir ad değişikliği talebin var. GİRVAK inceleyince sonucu bildireceğiz."
        )
    return isaret


class AdDegisikligiIsleyici:
    """Onay adı uygular; adla sahipliği kurulmuş kanıtın kalemleri yeniden
    değerlendirilmek üzere açılır ve kart arka planda hazırlanır. Ret adı korur."""

    async def uygula(
        self, oturum: AsyncSession, isaret: IncelemeIsareti, karar: str
    ) -> inceleme.KararEtkisi:
        not_eki = f" GİRVAK'ın notu: {isaret.girvak_notu}" if isaret.girvak_notu else ""
        if karar != KAPANDI:
            return inceleme.KararEtkisi(
                bildirim_turu=TUR_AD_DEGISIKLIGI_SONUCU,
                bildirim_metni="Ad değişikliği talebin onaylanmadı; adın aynı kaldı." + not_eki,
            )
        kullanici = await oturum.get(Kullanici, isaret.kullanici_id)
        yeni_ad = isaret.ayrinti["yeni_ad"]
        kullanici.ad = yeni_ad
        isler = await _ada_dayali_kanitlari_yeniden_ac(oturum, kullanici.id)
        return inceleme.KararEtkisi(
            bildirim_turu=TUR_AD_DEGISIKLIGI_SONUCU,
            bildirim_metni=f"Ad değişikliği talebin onaylandı. Adın artık “{yeni_ad}”." + not_eki,
            arka_plan=isler,
        )


async def _ada_dayali_kanitlari_yeniden_ac(
    oturum: AsyncSession, kullanici_id
) -> tuple[inceleme.ArkaPlanIsi, ...]:
    """Sahipliği adla kurulmuş parçaların kalemleri "değerlendirilmedi"ye döner;
    kart hazırlama onları yeni adla yeniden değerlendirir."""
    kart = await oturum.scalar(
        select(YetenekKarti).where(YetenekKarti.kullanici_id == kullanici_id)
    )
    if kart is None:
        return ()
    cikti_idleri = select(KanitParcasi.somut_cikti_id).where(
        KanitParcasi.sahiplik_kaynagi == SahiplikKaynagi.AD.value,
        KanitParcasi.somut_cikti_id.in_(
            select(SomutCikti.id).where(SomutCikti.yetenek_karti_id == kart.id)
        ),
    )
    sonuc = await oturum.execute(
        update(GuvenSkoru)
        .where(GuvenSkoru.somut_cikti_id.in_(cikti_idleri))
        .values(degerlendirme_tarihi=None)
    )
    if not sonuc.rowcount:
        return ()
    # Fonksiyon çağrı anında okunur: testler kart_hazirlama.karti_hazirla'yı sahteyle değiştirir.
    return (inceleme.ArkaPlanIsi(kart_hazirlama.karti_hazirla, (kart.id, kart.versiyon)),)
