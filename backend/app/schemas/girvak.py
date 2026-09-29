"""GİRVAK paneli şemaları (docs/faz-b-kimlik-ve-dongu.md § 7)."""

from __future__ import annotations

from pydantic import BaseModel


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
    # Firma akışı: kapanan ilanlar nedenleriyle.
    kapanan_ihtiyaclar: KapananIhtiyaclar = KapananIhtiyaclar()
