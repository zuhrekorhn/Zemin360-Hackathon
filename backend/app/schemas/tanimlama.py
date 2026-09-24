"""Tanımlama Ajanı uç noktalarının istek/yanıt şemaları.

docs/api-contracts.md § Tanımlama, docs/data-schema.md § IHTIYAC_KARTI.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr


class IhtiyacTaslagi(BaseModel):
    """Kuruma onay için gösterilen taslak — henüz veritabanında değil."""

    problem_tanimi: str | None = None
    basari_kriteri: str | None = None
    kisitlar: str | None = None
    # Eşleştirme'nin sert filtresi bu iki alandan çalışıyor (data-schema.md)
    sehir_tercihi: str | None = None
    musaitlik_tercihi: str | None = None


class TanimlamaSohbetYaniti(BaseModel):
    oturum_id: uuid.UUID
    soru: str | None = None
    taslak: IhtiyacTaslagi
    taslak_hazir: bool


class KurumGirdisi(BaseModel):
    """Kart bir kuruma bağlı (data-schema.md: IHTIYAC_KARTI.kurum_id).

    Kurum kaydı iletişim e-postasıyla bulunur/oluşturulur — Keşif'in
    Kullanici ile yaptığının aynısı. Giriş/kayıt akışı Faz 3'te gelecek.
    """

    ad: str
    sektor: str | None = None
    sehir: str | None = None
    iletisim_email: EmailStr


class IhtiyacKartiOnaylaIstegi(BaseModel):
    oturum_id: uuid.UUID
    kurum: KurumGirdisi
    duzeltilmis_taslak: IhtiyacTaslagi | None = None


class KurumYaniti(BaseModel):
    """Kartla birlikte gösterilen kurum bilgisi — iletişim e-postası YOK.

    `id` gerekli: Eşleştirme önerileri kurum kimliğiyle okunuyor
    (`GET /eslestirme/oneriler/{kurum_id}`), kartı onaylayan arayüzün bu
    kimliği öğrenebileceği başka bir yer yoktu. Kimlik iletişim bilgisi
    değil — gizlilik kuralı (agent-specs.md § 1.5) etkilenmiyor.
    """

    id: uuid.UUID
    ad: str
    sektor: str | None
    sehir: str | None


class IhtiyacKartiYaniti(BaseModel):
    """Kartın dışarıya açılan hali.

    Eşleştirme Ajanı da bu görünümü okuyacak (api-contracts.md). Kurumun
    iletişim e-postası burada yok: Keşif tarafındaki gizlilik kuralının
    karşılığı (agent-specs.md § 1.5) — iletişim iki taraf da onaylayınca açılır.
    """

    id: uuid.UUID
    problem_tanimi: str
    basari_kriteri: str | None
    kisitlar: str | None
    sehir_tercihi: str | None
    musaitlik_tercihi: str | None
    embedding_var: bool
    kurum: KurumYaniti
