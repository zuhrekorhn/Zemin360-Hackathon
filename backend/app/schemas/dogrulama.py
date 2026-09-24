"""Doğrulama Ajanı uç noktalarının şemaları (docs/api-contracts.md § Doğrulama)."""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, EmailStr, Field


class KanitEkleIstegi(BaseModel):
    """Mevcut bir somut çıktıya kanıt (ve isteğe bağlı referans) ekler."""

    somut_cikti_id: uuid.UUID
    kanit_linki: str | None = None
    kanit_turu: str | None = None
    # Verilirse tek kullanımlık referans isteği açılır
    referans_email: EmailStr | None = None


class GuvenSkoruYaniti(BaseModel):
    """Dört bileşen ayrı ayrı gösterilir — tek sayıya indirilmez.

    docs/agent-specs.md § 4: "her biri 0-3 puan, tek sayıya indirilmez".
    """

    kanit_orijinalligi: int
    sonuc_olculebilirligi: int
    rol_netligi: int
    ucuncu_taraf_onayi: int
    gerekce_metni: str | None

    model_config = {"from_attributes": True}


class ReferansDurumuYaniti(BaseModel):
    id: uuid.UUID
    referans_email: str
    durum: str
    puan: int | None
    yanit_metni: str | None
    olusturma_tarihi: dt.datetime
    # SMTP kurmuyoruz (MVP kararı): link yanıtta gösteriliyor ki referans
    # kişiye elle iletilebilsin.
    yanit_linki: str | None = None


class KanitDurumuYaniti(BaseModel):
    somut_cikti_id: uuid.UUID
    baslik: str
    kanit_linki: str | None
    link_erisilebilir: bool | None
    guven_skoru: GuvenSkoruYaniti | None
    referanslar: list[ReferansDurumuYaniti]


class ReferansIstegiYaniti(BaseModel):
    """Referans kişinin yanıt vermeden ÖNCE gördüğü bilgi.

    Neyi onayladığını bilmeden puan vermek anlamsız; iddianın başlığı ve
    açıklaması bu yüzden burada.

    `iddia_sahibi_adi` DÖNÜYOR, iletişim bilgisi DÖNMÜYOR: referans kişi kimin
    için konuştuğunu bilmeli, yoksa yanıtı bir şey ifade etmez — zaten iddia
    sahibi onu bizzat referans gösterdi, taraflar birbirini tanıyor. E-posta,
    telefon ve kartın geri kalanı burada yok; bu uç nokta girişsiz çalıştığı
    için yalnızca yanıt vermeye yetecek kadarını açıyor (agent-specs.md § 1.5
    aynı çizgide: kart görünür, iletişim iki taraf da onaylayınca açılır).
    """

    somut_cikti_id: uuid.UUID
    baslik: str
    aciklama: str | None
    iddia_sahibi_adi: str
    # "bekliyor" | "yanitlandi" | "yanit_yok"
    durum: str
    # Arayüz formu gösterip göstermeyeceğine buna bakarak karar verir.
    yanitlanabilir: bool


class ReferansYanitiIstegi(BaseModel):
    """Girişsiz uç nokta: kimlik yerine tek kullanımlık token.

    Referans kişiyi üye olmaya zorlamak yanıt oranını düşürür
    (docs/api-contracts.md § Mimari Notlar).
    """

    token: str
    # 1-5 skala; rubriğin 0-3'üne çevrilir (app/agents/dogrulama.py)
    puan: int = Field(ge=1, le=5)
    yorum: str | None = None


class ItirazIstegi(BaseModel):
    somut_cikti_id: uuid.UUID
    # Kullanıcı kanıtı düzelttiyse yeni link; boşsa mevcut kanıt yeniden değerlendirilir
    yeni_kanit_linki: str | None = None
    aciklama: str | None = None
