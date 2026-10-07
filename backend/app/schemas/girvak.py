"""GİRVAK paneli şemaları (docs/kimlik-ve-dongu.md § 7)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    """Toplam sayıların eşleşme türüne göre kırılımı (docs/kararlar.md F19).

    Toplamlar (`eslesme`, `isbirligi_durumlari`, hedefler) iki türü birlikte sayar.
    """

    genc_firma: TurSayilari = TurSayilari()
    firma_firma: TurSayilari = TurSayilari()


class KapananIhtiyaclar(BaseModel):
    """Kapanan ilanlar, firmanın seçtiği nedene göre (docs/kararlar.md F7).

    `nedensiz`: neden alanı eklenmeden kapanmış ilanlar.
    """

    platformda_bulundu: int = 0
    baska_yoldan_bulundu: int = 0
    vazgecildi: int = 0
    # Giriş hatası: program sonucu değil, ayrı gösterilir.
    hatali_girildi: int = 0
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
    # Duruma göre; `tamamlandi` = tamamlanmış iş birliği (program hedefi: 5).
    isbirligi_durumlari: IsbirligiSayilari
    # Program hedefleri (app/core/program.py), sabit sırayla.
    hedefler: list[HedefSayisi]
    # Firma akışı: kapanan ilanlar nedenleriyle ve eşleşme türüne göre kırılım.
    kapanan_ihtiyaclar: KapananIhtiyaclar = KapananIhtiyaclar()
    kirilim: EslesmeKirilimi = EslesmeKirilimi()


class OnayBekleyenFirma(BaseModel):
    """GİRVAK'ın doğrulama listesi (docs/kararlar.md F6).

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


# --- İnceleme kuyruğu (docs/dogrulama.md § 9) -----------------------------


class IncelemeSatiri(BaseModel):
    id: uuid.UUID
    tur: str
    durum: str
    olusturma_tarihi: dt.datetime
    kapanma_tarihi: dt.datetime | None
    girvak_notu: str | None
    genc_adi: str | None
    # Gencin kartı (GİRVAK kart sayfasını açar); kartı yoksa None.
    kart_id: uuid.UUID | None
    somut_cikti_id: uuid.UUID | None
    cikti_basligi: str | None
    # Türe özel bağlam (ör. eski ve istenen ad, itiraz notları).
    ayrinti: dict


class IncelemeKarariIstegi(BaseModel):
    # kapandi: "sorun yok" (talepte "onayla"); dogrulanamadi: talepte "reddet".
    karar: Literal["kapandi", "dogrulanamadi"]
    girvak_notu: str | None = Field(default=None, max_length=500)
