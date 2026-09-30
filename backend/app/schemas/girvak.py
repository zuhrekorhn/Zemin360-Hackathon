"""GİRVAK paneli şemaları (docs/faz-b-kimlik-ve-dongu.md § 7)."""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict

from app.core.firma_dogrulama import AlanAdiIpucu, GirvakKarari


class HesapSayilari(BaseModel):
    genc: int
    kurum: int
    girvak: int


class EslesmeSayilari(BaseModel):
    onerildi: int
    ilgileniliyor: int
    kabul_edildi: int
    reddedildi: int
    genc_ilgilendi: int = 0
    kapandi: int = 0


class IsbirligiSayilari(BaseModel):
    plan_bekliyor: int
    aktif: int
    tamamlandi: int


class TurSayilari(BaseModel):
    """Bir eşleşme türünün (genç–firma ya da firma–firma) sayıları."""

    oneri: int = 0
    karsilikli_ilgi: int = 0
    isbirligi: int = 0
    tamamlanan: int = 0


class EslesmeKirilimi(BaseModel):
    """Toplam sayıların eşleşme türüne göre kırılımı (docs/plans/firma-akisi.md § 0 karar 19).

    Toplamlar (`eslesme`, `isbirligi_durumlari`, hedefler) iki türü birlikte sayar.
    """

    genc_firma: TurSayilari = TurSayilari()
    firma_firma: TurSayilari = TurSayilari()


class KapananIhtiyaclar(BaseModel):
    """Kapanan ilanlar, firmanın seçtiği nedene göre (firma-akisi § 0 karar 7).

    `nedensiz`: neden alanı eklenmeden kapanmış ilanlar.
    """

    platformda_bulundu: int = 0
    baska_yoldan_bulundu: int = 0
    vazgecildi: int = 0
    nedensiz: int = 0


class HedefSayisi(BaseModel):
    """Program hedefi: programın adı + platformda ne sayıldığı (fark gizlenmez)."""

    anahtar: str
    program_adi: str
    olcum: str
    sayi: int
    hedef: int


class Sayilar(BaseModel):
    hesap: HesapSayilari
    yetenek_karti: int
    ihtiyac_karti: int
    eslesme: EslesmeSayilari
    isbirligi: int
    # Faz C: duruma göre; `tamamlandi` = tamamlanmış pilot (Faz D hedefi: 5).
    isbirligi_durumlari: IsbirligiSayilari
    # Faz D: program hedefleri (app/core/program.py), sabit sırayla.
    hedefler: list[HedefSayisi]
    # Firma akışı: kapanan ilanlar nedenleriyle ve eşleşme türüne göre kırılım.
    kapanan_ihtiyaclar: KapananIhtiyaclar = KapananIhtiyaclar()
    kirilim: EslesmeKirilimi = EslesmeKirilimi()


class OnayBekleyenFirma(BaseModel):
    """GİRVAK'ın doğrulama listesi (docs/plans/firma-akisi.md § 6).

    Tam e-posta dönmez; yalnızca alan adı (ipucunun dayanağı). İletişim
    bilgisi GİRVAK'ın işi değil (eşleşmedeki kuralla aynı).
    """

    kurum_id: uuid.UUID
    ad: str
    tur: str | None
    sektor: str | None
    sehir: str | None
    web_sitesi: str | None
    eposta_alan_adi: str | None
    ipucu: AlanAdiIpucu
    dogrulama_durumu: str
    dogrulama_tarihi: dt.datetime | None
    kayit_tarihi: dt.datetime


class FirmaDogrulamaIstegi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    karar: GirvakKarari
