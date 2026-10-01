"""Ön rubrik: modelin üç başlığı puanlaması (docs/agent-specs.md § 4.3).

Geçici modül: plan § 11'deki "model gerçek çıkarır, kural puanlar" çekirdeği
gelince yerini ona bırakır (docs/plans/dogrulama-iyilestirme.md, adım 4).
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from app.agents.dogrulama.link_kontrolu import LinkKontrolu
from app.core.kullanici_dili import KULLANICI_DILI_KURALLARI
from app.core.llm import llm_hatasini_cevir, yedekli_zincir

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
RUBRIK_TALIMATI += KULLANICI_DILI_KURALLARI

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


@lru_cache
def _rubrik_zinciri() -> Runnable:
    # Güçlü katman: rubrik kanıtla iddiayı karşılaştırıp gerekçeli puan veriyor;
    # nüans ve kurallara (itiraz notu beyandır vb.) uyum burada önemli.
    return yedekli_zincir(
        "guclu",
        "dogrulama_rubrik",
        lambda m: RUBRIK_SABLONU | m.with_structured_output(RubrikPuani),
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
