"""Doğrulama Ajanı — somut çıktı iddialarına dört bileşenli güven göstergesi.

**Sohbet ajanı değil** (Eşleştirme gibi): çok turlu konuşma yok, üç ayrı
tek seferlik akış var — kanıt kontrolü, referans akışı, itiraz. Bu yüzden
`sohbet_motoru.py` kullanılmıyor.

docs/agent-specs.md § 4. Sınırlar oradan:
  - "Bu kişi yalan söylüyor" gibi kesin hüküm vermez, sinyal toplar.
  - Kanıtsız kartı sistemden dışlamaz, sadece "doğrulanmamış" etiketler.
  - Üçüncü taraf onayını zorunlu kılmaz — zaman aşımı bir ceza değil, nötr
    bir durumdur (docs/sequence-diagrams.md § Akış 2, else dalı).
  - Rubrik kriterleri objektif ve kontrol edilebilir olmalı; "ne kadar
    etkileyici yazılmış" gibi öznel kriterler önyargı üretir (madde 5).
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from functools import lru_cache

import httpx
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from app.core.llm import HizSinirHatasi, kota_hatasi_mi, model, yedekli_zincir

# Referans yanıtı için tanınan süre (docs/agent-specs.md § 4.2: 5-7 gün).
# Üst sınır seçildi: erken "yanıt yok" demek referans kişiyi cezalandırır.
REFERANS_TIMEOUT_GUN = 7

DURUM_BEKLIYOR = "bekliyor"
# "onaylandi" değil: referans olumsuz de yanıtlayabilir, durum yalnızca
# yanıtın geldiğini söyler. Değerlendirme ucuncu_taraf_onayi puanında.
DURUM_YANITLANDI = "yanitlandi"
DURUM_YANIT_YOK = "yanit_yok"

# 1-5 referans skalasını rubriğin 0-3 aralığına indirger.
# 3 ("ne iyi ne kötü") bir onay değildir, o yüzden 2'den fazlasını vermiyor;
# tam puan yalnızca açık bir olumlu referansta (5) veriliyor.
REFERANS_PUAN_ESLEMESI = {1: 0, 2: 1, 3: 1, 4: 2, 5: 3}

LINK_TIMEOUT_SANIYE = 8
# Sayfanın tamamı çekilmiyor; başlık/meta için ilk parça yeterli (basit tut).
INDIRILEN_BAYT = 20_000

RUBRIK_TALIMATI = """Sen Zemin360'ın Doğrulama Ajanı'sın. Bir gencin "şunu yaptım"
iddiasını, verdiği kanıtla birlikte puanlıyorsun.

Ne YAPMAYACAKSIN:
- "Bu kişi yalan söylüyor" gibi hüküm verme. Sinyal topluyorsun, karar vermiyorsun.
- Yazının ne kadar etkileyici/akıcı olduğuna BAKMA. İyi yazan kişiye avantaj
  vermek önyargı üretir.
- Kanıt yoksa cezalandırma; sadece o bileşene düşük puan ver.

Üç bileşeni 0-3 arası puanla. Ölçütler objektif ve kontrol edilebilir:

kanit_orijinalligi:
  0 = kanıt linki yok veya açılmıyor
  1 = link açılıyor ama içeriği iddiayla ilgisiz görünüyor
  2 = link açılıyor, iddiayla ilgili ama kişinin kendi işi olduğu belirsiz
  3 = link açılıyor ve iddia edilen işin kendisine götürüyor (repo, yayın, ürün)

sonuc_olculebilirligi:
  0 = hiçbir sonuç belirtilmemiş
  1 = sonuç var ama tamamen niteliksel ("çok işe yaradı")
  2 = sayı var ama neyin ölçüsü olduğu net değil
  3 = sayı/oran/süre var ve neyi ölçtüğü açık ("400 kitap takip ediliyor")

rol_netligi:
  0 = kişinin ne yaptığı hiç yazmıyor
  1 = "katkıda bulundum" gibi belirsiz ifade
  2 = rol yazılmış ama ekip içindeki payı belirsiz
  3 = kişinin ne yaptığı açık ve spesifik ("backend'i ben yazdım")

gerekce_metni: 2 cümle. Hangi bileşene neden o puanı verdiğini, kanıttaki
somut şeylere atıfla açıkla. Genel geçer laf etme.
"""

RUBRIK_SABLONU = ChatPromptTemplate.from_messages(
    [
        ("system", RUBRIK_TALIMATI),
        (
            "human",
            "İDDİA\n"
            "Başlık: {baslik}\n"
            "Açıklama: {aciklama}\n\n"
            "KANIT\n"
            "Link: {kanit_linki}\n"
            "Link durumu: {link_durumu}\n"
            "Linkten okunan başlık/açıklama: {link_ozeti}\n\n"
            "Bu iddiayı puanla.",
        ),
    ]
)


class RubrikPuani(BaseModel):
    """LLM'in ürettiği ön rubrik (üçüncü taraf onayı buraya dahil değil)."""

    kanit_orijinalligi: int = Field(ge=0, le=3)
    sonuc_olculebilirligi: int = Field(ge=0, le=3)
    rol_netligi: int = Field(ge=0, le=3)
    gerekce_metni: str


@dataclass(frozen=True)
class LinkKontrolu:
    erisilebilir: bool
    durum_kodu: int | None
    ozet: str
    aciklama: str


# --- Saf hesap (LLM ve ağ olmadan test edilebilir) -------------------------


def referans_puanina_cevir(skala_1_5: int) -> int:
    """Referansın 1-5 puanını rubriğin 0-3 aralığına indirger."""
    if skala_1_5 not in REFERANS_PUAN_ESLEMESI:
        raise ValueError("Referans puanı 1-5 aralığında olmalı")
    return REFERANS_PUAN_ESLEMESI[skala_1_5]


def zaman_asimina_ugradi_mi(
    olusturma_tarihi: dt.datetime, durum: str, simdi: dt.datetime | None = None
) -> bool:
    """Bekleyen bir referans isteği süresini doldurmuş mu?

    Ayrı bir zamanlayıcı yok (bkz. Eşleştirme'deki aynı karar): bu geçiş
    okuma anında hesaplanıyor.
    """
    if durum != DURUM_BEKLIYOR:
        return False
    an = simdi or dt.datetime.now(dt.UTC)
    if olusturma_tarihi.tzinfo is None:
        olusturma_tarihi = olusturma_tarihi.replace(tzinfo=dt.UTC)
    return an - olusturma_tarihi >= dt.timedelta(days=REFERANS_TIMEOUT_GUN)


def linki_normalize_et(kanit_linki: str) -> str:
    """Şeması olmayan linke https:// ekler.

    Kullanıcılar sohbette linki çoğu zaman "github.com/..." diye yazıyor;
    şemasız adres httpx'e verilemez ve kanıt haksız yere "açılmıyor" sayılır.
    """
    link = kanit_linki.strip()
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", link):
        return link
    return f"https://{link.lstrip('/')}"


def link_ozetini_cikar(html: str) -> str:
    """Sayfadan başlık ve meta açıklamasını alır (tam içerik çekilmiyor)."""
    baslik = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    meta = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.S | re.I
    )
    parcalar = [p.group(1).strip() for p in (baslik, meta) if p]
    ozet = " — ".join(" ".join(parca.split()) for parca in parcalar)
    return ozet[:400] or "(başlık/açıklama okunamadı)"


# --- Kanıt kontrolü --------------------------------------------------------


async def linki_kontrol_et(kanit_linki: str | None) -> LinkKontrolu:
    """Link gerçekten açılıyor mu? İçerik analizi yok, erişilebilirlik var."""
    if not kanit_linki:
        return LinkKontrolu(False, None, "(kanıt linki verilmedi)", "kanıt linki yok")

    adres = linki_normalize_et(kanit_linki)
    try:
        async with httpx.AsyncClient(timeout=LINK_TIMEOUT_SANIYE, follow_redirects=True) as istemci:
            yanit = await istemci.get(adres)
            govde = yanit.text[:INDIRILEN_BAYT] if yanit.is_success else ""
    except httpx.HTTPError as hata:
        return LinkKontrolu(False, None, "(sayfa açılmadı)", f"erişilemedi: {type(hata).__name__}")

    if not yanit.is_success:
        return LinkKontrolu(
            False, yanit.status_code, "(sayfa açılmadı)", f"HTTP {yanit.status_code}"
        )

    return LinkKontrolu(True, yanit.status_code, link_ozetini_cikar(govde), "açılıyor")


@lru_cache
def _rubrik_zinciri() -> Runnable:
    return yedekli_zincir(
        lambda model_adi: RUBRIK_SABLONU | model(model_adi).with_structured_output(RubrikPuani)
    )


async def rubrik_puanla(
    *, baslik: str, aciklama: str | None, kanit_linki: str | None, kontrol: LinkKontrolu
) -> RubrikPuani:
    """Ön rubrik puanı (docs/agent-specs.md § 4.3).

    `ucuncu_taraf_onayi` burada YOK — referans yanıtı gelmeden o bileşen 0
    kalır ve referans geldiğinde ayrıca güncellenir.
    """
    try:
        puan: RubrikPuani = await _rubrik_zinciri().ainvoke(
            {
                "baslik": baslik,
                "aciklama": aciklama or "(açıklama yazılmamış)",
                "kanit_linki": kanit_linki or "(yok)",
                "link_durumu": kontrol.aciklama,
                "link_ozeti": kontrol.ozet,
            }
        )
    except Exception as hata:
        if kota_hatasi_mi(hata):
            raise HizSinirHatasi(str(hata)) from hata
        raise

    # Link hiç açılmıyorsa orijinallik puanı 0'ı aşamaz — bu ölçülebilir bir
    # olgu, LLM'in takdirine bırakılmıyor.
    if not kontrol.erisilebilir:
        puan = puan.model_copy(update={"kanit_orijinalligi": 0})
    return puan
