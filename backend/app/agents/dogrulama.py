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
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache

import httpx
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from app.core.llm import llm_hatasini_cevir, model, yedekli_zincir

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
# Sayfanın tamamı çekilmiyor: <head> bitene kadar okunuyor. Sabit bir ilk
# parça yetmiyordu — GitHub gibi siteler <title>'ı 20 KB'ın ötesine atıyor.
# Üst sınır, <head>'i hiç kapatmayan sayfalarda okumayı durdurmak için.
INDIRILEN_BAYT = 300_000

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

İTİRAZ NOTU (varsa):
Kullanıcı önceki puana itiraz ettiyse notu sana iletiliyor. Bu not
DOĞRULANMIŞ BİLGİ DEĞİL, kullanıcının kendi beyanıdır:
- Notun işaret ettiği yeri kanıtta ve açıklamada TEKRAR kontrol et; gözden
  kaçırdığın bir şey varsa puanı düzelt.
- Notun kendisi kanıt yerine geçmez. "Backend'i ben yazdım" demesi tek başına
  rol_netligi 3 ettirmez; tam puan ancak kanıtta ya da açıklamada karşılığı
  görülüyorsa verilir.
- Yalnızca beyan olarak kalan bir not en fazla bir basamak yukarı taşır,
  tam puana (3) tek başına yetmez.
- Notun tonuna, ısrarına ya da uzunluğuna bakma.

gerekce_metni: 2 cümle. Hangi bileşene neden o puanı verdiğini, kanıttaki
somut şeylere atıfla açıkla. Genel geçer laf etme. İtiraz notunu dikkate
aldıysan bunu söyle.
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
            "KULLANICININ İTİRAZ NOTU (beyan, doğrulanmamış)\n"
            "{itiraz_notu}\n\n"
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


def ucuncu_taraf_onayi_hesapla(puanlar: Sequence[int]) -> int:
    """Yanıtlamış tüm referanslardan tek bir 0-3 puanı üretir.

    Ortalama alınıyor, en yüksek değil: en yüksek, "olumlu diyen birini
    bulana kadar referans sor" davranışını ödüllendirirdi. Ortalama, zayıf
    bir referansın puanı aşağı çekmesine izin verir — göstergenin işi
    sinyal taşımak, parlatmak değil.

    Ortalama normal (0.5 yukarı) yuvarlanıyor: aşağı yuvarlamak iki güçlü
    referansı (5+4 → 2.5 → 2) tek bir 5'ten (3) daha düşük gösteriyordu.
    Referans eklemek puanı düşürmemeli. Python'ın round()'u 2.5'i 2'ye
    çevirdiği için (bankacı yuvarlaması) elle +0.5 uygulanıyor.
    """
    if not puanlar:
        return 0
    cevrilmis = [referans_puanina_cevir(p) for p in puanlar]
    return math.floor(sum(cevrilmis) / len(cevrilmis) + 0.5)


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


def _meta_icerigi(html: str, anahtar: str) -> str | None:
    """`name=` veya `property=` ile verilmiş bir meta etiketinin içeriği.

    Open Graph etiketleri (og:title, og:description) `property=` kullanıyor;
    sıra da sabit değil, `content=` önce gelebiliyor.
    """
    kaliplar = (
        rf'<meta[^>]+(?:name|property)=["\']{anahtar}["\'][^>]*?content=["\'](.*?)["\']',
        rf'<meta[^>]+content=["\'](.*?)["\'][^>]*?(?:name|property)=["\']{anahtar}["\']',
    )
    for kalip in kaliplar:
        eslesme = re.search(kalip, html, re.S | re.I)
        if eslesme and eslesme.group(1).strip():
            return eslesme.group(1)
    return None


def link_ozetini_cikar(html: str) -> str:
    """Sayfadan başlık ve açıklamayı alır (tam içerik çekilmiyor).

    Başlık için <title>, yoksa og:title; açıklama için meta description,
    yoksa og:description.
    """
    baslik_etiketi = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    baslik = baslik_etiketi.group(1) if baslik_etiketi else _meta_icerigi(html, "og:title")
    aciklama = _meta_icerigi(html, "description") or _meta_icerigi(html, "og:description")

    parcalar = [" ".join(p.split()) for p in (baslik, aciklama) if p and p.strip()]
    ozet = " — ".join(parcalar)
    return ozet[:400] or "(başlık/açıklama okunamadı)"


# --- Kanıt kontrolü --------------------------------------------------------


async def linki_kontrol_et(kanit_linki: str | None) -> LinkKontrolu:
    """Link gerçekten açılıyor mu? İçerik analizi yok, erişilebilirlik var."""
    if not kanit_linki:
        return LinkKontrolu(False, None, "(kanıt linki verilmedi)", "kanıt linki yok")

    adres = linki_normalize_et(kanit_linki)
    try:
        async with httpx.AsyncClient(timeout=LINK_TIMEOUT_SANIYE, follow_redirects=True) as istemci:
            async with istemci.stream("GET", adres) as yanit:
                if not yanit.is_success:
                    return LinkKontrolu(
                        False, yanit.status_code, "(sayfa açılmadı)", f"HTTP {yanit.status_code}"
                    )
                govde = await _basligi_oku(yanit)
    except httpx.HTTPError as hata:
        return LinkKontrolu(False, None, "(sayfa açılmadı)", f"erişilemedi: {type(hata).__name__}")

    return LinkKontrolu(True, yanit.status_code, link_ozetini_cikar(govde), "açılıyor")


async def _basligi_oku(yanit: httpx.Response) -> str:
    """Sayfayı `</head>` görülene ya da üst sınıra kadar okur.

    İndirmeyi erken kesiyoruz: ihtiyacımız olan her şey <head> içinde ve
    büyük sayfaların gövdesini çekmenin anlamı yok.
    """
    parcalar: list[str] = []
    uzunluk = 0
    async for parca in yanit.aiter_text():
        parcalar.append(parca)
        uzunluk += len(parca)
        if "</head>" in parca.lower() or uzunluk >= INDIRILEN_BAYT:
            break
    return "".join(parcalar)


@lru_cache
def _rubrik_zinciri() -> Runnable:
    return yedekli_zincir(
        lambda model_adi: RUBRIK_SABLONU | model(model_adi).with_structured_output(RubrikPuani)
    )


async def rubrik_puanla(
    *,
    baslik: str,
    aciklama: str | None,
    kanit_linki: str | None,
    kontrol: LinkKontrolu,
    itiraz_notu: str | None = None,
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
                "itiraz_notu": itiraz_notu or "(itiraz yok)",
            }
        )
    except Exception as hata:
        cevrilmis = llm_hatasini_cevir(hata)
        raise cevrilmis from hata

    # Link hiç açılmıyorsa orijinallik puanı 0'ı aşamaz — bu ölçülebilir bir
    # olgu, LLM'in takdirine bırakılmıyor.
    if not kontrol.erisilebilir:
        puan = puan.model_copy(update={"kanit_orijinalligi": 0})
    return puan
