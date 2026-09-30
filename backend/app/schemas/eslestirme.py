"""Eşleştirme Ajanı uç noktalarının şemaları (docs/api-contracts.md § Eşleştirme)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel

from app.schemas.kesif import YetenekKartiYaniti
from app.schemas.tanimlama import IhtiyacKartiYaniti


class EslestirmeCalistirIstegi(BaseModel):
    """Kurum için boş bırakılır: kurum token'dan alınır. GİRVAK hangi kurum
    için çalıştırdığını söylemek zorunda."""

    kurum_id: uuid.UUID | None = None
    # Verilmezse kurumun en son ihtiyaç kartı.
    ihtiyac_karti_id: uuid.UUID | None = None


class Iletisim(BaseModel):
    """Kabulle açılan e-postalar (docs/faz-b-kimlik-ve-dongu.md § 5).

    Yalnızca `kabul_edildi` durumunda ve yalnızca eşleşmenin iki tarafına
    dolu döner; başka her durumda ve GİRVAK'a `iletisim` alanı `null`.
    Adlar burada değil: iletişim bilgisi sayılmıyor, kart görünümünde baştan var.
    """

    # Genç ilanında gencin, ortak ilanında aday firmanın e-postası (tam biri dolu).
    genc_email: str | None = None
    aday_firma_email: str | None = None
    kurum_email: str | None


class FirmaAdayKarti(BaseModel):
    """Ortak ilanında önerilen firma (docs/plans/firma-akisi.md § 0 kararlar 16-17).

    İletişim e-postası YOK: yalnızca karşılıklı ilgide `iletisim`'de açılır.
    Doğrulama durumunun kendisi değil, yalnızca işareti.
    """

    firma_karti_id: uuid.UUID
    kurum_id: uuid.UUID
    firma_adi: str
    tur: str | None
    sektor: str | None
    sehir: str | None
    dogrulandi: bool
    ne_yapiyoruz: str
    yetkinlikler: list[str]
    onceki_isler: str | None
    isbirligi_turleri: list[str]
    # Aday olarak tamamladığı iş birlikleri ("tamamlanan iş birliği" rozeti)
    tamamlanan_isbirligi: int = 0


class OneriYaniti(BaseModel):
    """Kuruma gösterilen tek bir öneri.

    Yetenek kartı e-posta taşımaz (agent-specs.md § 1.5) — Keşif'in kart
    şeması aynen kullanılıyor; e-postalar kabulden sonra `iletisim`'de.
    """

    eslesme_id: uuid.UUID
    skor: float
    durum: str
    gerekce_metni: str | None
    # Aday türü ilanın kapısına göre: genç ilanında yetenek kartı, ortak
    # ilanında firma kartı (tam biri dolu; docs/plans/firma-akisi.md § 4).
    aday_turu: Literal["genc", "firma"] = "genc"
    yetenek_karti: YetenekKartiYaniti | None = None
    firma_karti: FirmaAdayKarti | None = None
    iletisim: Iletisim | None = None
    # Genç ilgi gösterdi, firmanın yanıtı bekleniyor. Skoru değiştirmez;
    # firma ekranında ayrı bir işaret ve bölüm (plan § 7.1).
    genc_ilgi_gosterdi: bool = False


class OnerilerYaniti(BaseModel):
    ihtiyac_karti_id: uuid.UUID
    oneriler: list[OneriYaniti]
    # Havuz küçükken sonuç azlığı gizlenmez, açıkça söylenir
    # (docs/matching-algorithm.md § 5, cold start).
    az_sonuc_uyarisi: bool
    # Liste boş kaldığında arayüz "neden boş"u söyleyebilsin diye eşik
    # yanıtta dönüyor; istemci tarafında sabit tutulursa ikisi ayrışır.
    skor_esigi: float


class IlgileniyorumIstegi(BaseModel):
    eslesme_id: uuid.UUID


class EslesmeDurumYaniti(BaseModel):
    """İlgileniyorum / kabul / red sonrası eşleşmenin durumu.

    İş birliği yalnızca gencin kabulüyle açılır; öncesinde `isbirligi_id` ve
    `iletisim` boş.
    """

    eslesme_id: uuid.UUID
    durum: str
    isbirligi_id: uuid.UUID | None = None
    iletisim: Iletisim | None = None


class BanaGelenIlgi(BaseModel):
    """Gencin kartına gelen ilgi: kurum "ilgileniyorum" dedikten sonra görünür."""

    eslesme_id: uuid.UUID
    durum: str
    son_aktivite_tarihi: dt.datetime
    yetenek_karti_id: uuid.UUID
    rol_alani: str
    ihtiyac_karti: IhtiyacKartiYaniti
    isbirligi_id: uuid.UUID | None = None
    iletisim: Iletisim | None = None


class GencEslesmesi(BaseModel):
    """Gencin ana sayfasındaki bir satır: fırsat (önerildi) ya da kendi ilgisi.

    `uyum` eşleşmenin skoru (0-1; arayüz "%72 uyum" yazar). `gerekce_metni`
    firmaya yazılan açıklamanın aynısı (plan § 0 karar 9; başlık "Neden uygun?").
    E-posta yalnızca karşılıklı ilgide `iletisim`'de.
    """

    eslesme_id: uuid.UUID
    durum: str
    uyum: float
    gerekce_metni: str | None
    son_aktivite_tarihi: dt.datetime
    yetenek_karti_id: uuid.UUID
    rol_alani: str
    ihtiyac_karti: IhtiyacKartiYaniti
    isbirligi_id: uuid.UUID | None = None
    iletisim: Iletisim | None = None


class FirmaAdayEslesmesi(BaseModel):
    """Aday firmanın gördüğü satır (docs/plans/firma-akisi.md § 0 karar 8).

    Ortak ilanında önerildiği ya da ilgi gördüğü/gösterdiği her eşleşme:
    arayüz fırsatlar, gelen ilgiler ve ilgilerimiz diye ayırır. `baslatan`
    ilk ilgiyi kimin gösterdiği (`genc` = aday tarafı, `kurum` = ilan tarafı;
    kolon adları karar 12 gereği değişmedi). E-posta yalnızca karşılıklı ilgide.
    """

    eslesme_id: uuid.UUID
    durum: str
    uyum: float
    gerekce_metni: str | None
    son_aktivite_tarihi: dt.datetime
    baslatan: str | None
    ihtiyac_karti: IhtiyacKartiYaniti
    isbirligi_id: uuid.UUID | None = None
    iletisim: Iletisim | None = None


class GencIlgiIstegi(BaseModel):
    """Genç ilgi gösterirken açık onay verir: firma da ilgilenirse e-postası
    firmayla paylaşılır. Onaysız istek 422."""

    iletisim_onayi: Literal[True]


class KurumOnerisi(BaseModel):
    """`GET /eslestirme/onerilerim` satırı: kurum panelindeki öneri özeti."""

    eslesme_id: uuid.UUID
    durum: str
    skor: float
    son_aktivite_tarihi: dt.datetime
    ihtiyac_karti_id: uuid.UUID
    problem_tanimi: str
    # Aday: genç (yetenek kartı) ya da firma (firma kartı); adı `aday_adi`'nda.
    aday_turu: Literal["genc", "firma"] = "genc"
    aday_adi: str
    yetenek_karti_id: uuid.UUID | None = None
    firma_karti_id: uuid.UUID | None = None
    # Yalnızca genç adayında (geriye dönük alanlar).
    genc_adi: str | None = None
    rol_alani: str | None = None
    iletisim: Iletisim | None = None


class Ilerleme(BaseModel):
    """İş birliği planının ilerlemesi; gecikme okuma anında hesaplanır."""

    tamamlanan: int
    toplam: int
    geciken: int


class IsbirligiOzeti(BaseModel):
    """`GET /isbirliklerim` satırı — iki tarafa da aynı görünüm."""

    isbirligi_id: uuid.UUID
    durum: str
    baslangic_tarihi: dt.date | None
    eslesme_id: uuid.UUID
    # Aday tarafı: genç ya da ortak firma (docs/plans/firma-akisi.md § 9).
    aday_turu: Literal["genc", "firma"] = "genc"
    aday_adi: str
    genc_adi: str | None = None
    kurum_adi: str
    rol_alani: str | None = None
    problem_tanimi: str
    iletisim: Iletisim
    # Takip (Faz C): plan_bekliyor | aktif | tamamlandi ve adım ilerlemesi.
    ilerleme: Ilerleme
