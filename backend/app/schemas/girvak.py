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


class IsbirligiSayilari(BaseModel):
    plan_bekliyor: int
    aktif: int
    tamamlandi: int


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
