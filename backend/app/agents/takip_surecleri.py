"""İş birliği süreç şablonları (docs/kararlar.md T1).

Saf modül: veritabanı ve LLM yok. Eşleşmenin türüne göre gerçek hayattaki
adımlar burada sabit; Takip Ajanı adımları UYDURMAZ, yalnızca her adımın
"ne olunca tamam sayılır" cümlesini ve hazırlık önerisini ilana göre
kişiselleştirir (app/agents/takip.py). Model başarısız olursa buradaki
metinler kullanılır: plan hiçbir zaman boş kalmaz.

Yeni bir süreç = `SABLONLAR`'a bir kayıt ve `surec_sec`'te bir kural;
ajan ve uçlar değişmez. Kullanıcıya görünen metinlerde "pilot" yok, "deneme
işi" var (docs/icerik-rehberi.md); `pilot` yalnızca koddaki anahtar.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.core.musaitlik import PROJE_BAZLI, STAJ

ISE_ALIM = "ise_alim"
STAJ_SURECI = "staj"
PROJE = "proje"
DENEME_ISI = "pilot"
TEDARIK = "tedarik"
ISBIRLIGI = "isbirligi"

SON_ADIM_TANIMI = (
    "İlandaki başarı kriterine göre birlikte değerlendirme yapıldı ve sonraki adıma karar verildi."
)


@dataclass(frozen=True)
class SablonAdimi:
    anahtar: str
    baslik: str
    # Ajan kişiselleştiremezse kullanılan metinler.
    tamam_tanimi: str
    oneri: str
    # Başlangıçtan itibaren kaçıncı haftanın sonu (taraflar düzenleyebilir).
    hafta: int


@dataclass(frozen=True)
class SurecSablonu:
    anahtar: str
    # Kullanıcıya görünen ad (iş birliği sayfasının başlığında).
    ad: str
    adimlar: tuple[SablonAdimi, ...]


@dataclass(frozen=True)
class PlanAdimi:
    """Plana yazılacak adım: şablon adımı + (varsa) ajanın kişiselleştirmesi."""

    anahtar: str
    baslik: str
    tamam_tanimi: str
    oneri: str
    hedef_tarih: dt.date


_TANISMA = SablonAdimi(
    "tanisma",
    "Tanışma görüşmesi",
    "İki taraf kısa bir görüşmede tanıştı, beklentiler konuşuldu.",
    "Görüşmeden önce ilanı ve karşı tarafın kartını birlikte gözden geçirin; "
    "sormak istediğiniz iki üç soruyu not alın.",
    1,
)
_TANISMA_TOPLANTISI = SablonAdimi(
    "tanisma",
    "Tanışma toplantısı",
    "İki firma bir toplantıda tanıştı, ihtiyaç ve beklentiler konuşuldu.",
    "Toplantıdan önce ilandaki problemi ve karşı firmanın kartını gözden geçirin; "
    "kimlerin katılacağını belirleyin.",
    1,
)
_ON_GORUSME = SablonAdimi(
    "on_gorusme",
    "Ön görüşme ve gizlilik",
    "Paylaşılacak bilgi netleşti, gerekiyorsa gizlilik anlaşması imzalandı.",
    "Hangi verinin paylaşılacağını ve kimlerin erişeceğini önceden konuşun.",
    2,
)

SABLONLAR: dict[str, SurecSablonu] = {
    ISE_ALIM: SurecSablonu(
        ISE_ALIM,
        "İşe alım süreci",
        (
            SablonAdimi(
                "gorusme_planlandi",
                "Tanışma görüşmesi planlandı",
                "Görüşmenin günü, saati ve şekli (yüz yüze ya da çevrim içi) belli.",
                "Uygun iki üç zaman önerin; görüşmenin ne kadar süreceğini baştan söyleyin.",
                1,
            ),
            SablonAdimi(
                "gorusme_yapildi",
                "Görüşme yapıldı",
                "Görüşme yapıldı; iki taraf da işin kapsamı hakkında fikir sahibi.",
                "İlandaki problemi örnek bir durum üzerinden konuşun; adayın benzer bir "
                "çalışmasını anlatmasını isteyin.",
                2,
            ),
            SablonAdimi(
                "deneme_gorevi",
                "Deneme görevi teslim edildi",
                "Kısa bir deneme görevi verildi ve teslim edildi.",
                "Görevi ilandaki problemin küçük bir parçası olarak seçin; birkaç saatte "
                "bitecek kadar küçük tutun.",
                3,
            ),
            SablonAdimi(
                "karar",
                "Karar verildi",
                "Firma kararını iletti: teklif ya da şimdilik değil.",
                "Kararı gerekçesiyle ve nazikçe iletin; teklifse başlangıç tarihini konuşun.",
                4,
            ),
            SablonAdimi(
                "ilk_ay",
                "İlk ay değerlendirmesi",
                SON_ADIM_TANIMI,
                "İlk ayın sonunda başarı kriterine ne kadar yaklaşıldığını birlikte konuşun.",
                8,
            ),
        ),
    ),
    STAJ_SURECI: SurecSablonu(
        STAJ_SURECI,
        "Staj süreci",
        (
            _TANISMA,
            SablonAdimi(
                "staj_plani",
                "Staj planı ve sorumlu kişi belirlendi",
                "Stajın süresi, çalışma günleri ve stajyerden sorumlu kişi belli.",
                "Stajyerin ilk hafta neyle başlayacağını ve kime soru soracağını yazın.",
                2,
            ),
            SablonAdimi(
                "staj_basladi",
                "Staj başladı",
                "Stajyer işe başladı; ilk görevini aldı.",
                "İlk görevi ilandaki problemle ilişkili ve küçük seçin.",
                3,
            ),
            SablonAdimi(
                "ara_degerlendirme",
                "Ara değerlendirme",
                "Stajın ortasında iki taraf ilerlemeyi konuştu.",
                "Neyin iyi gittiğini ve neyin değişmesi gerektiğini karşılıklı söyleyin.",
                6,
            ),
            SablonAdimi(
                "staj_sonu",
                "Staj sonu değerlendirmesi",
                SON_ADIM_TANIMI,
                "Stajyerin yaptığı işi başarı kriterine göre birlikte gözden geçirin.",
                10,
            ),
        ),
    ),
    PROJE: SurecSablonu(
        PROJE,
        "Proje süreci",
        (
            _TANISMA,
            SablonAdimi(
                "kapsam",
                "Kapsam ve teslim tarihi netleşti",
                "Neyin teslim edileceği ve son teslim tarihi yazılı olarak belli.",
                "Teslim edilecek işi maddeler halinde yazın; kapsam dışı olanı da belirtin.",
                2,
            ),
            SablonAdimi(
                "ilk_teslim",
                "İlk teslim",
                "İşin ilk hali teslim edildi.",
                "İlk teslimi erken ve küçük tutun; yön doğru mu, bunu görmek yeter.",
                4,
            ),
            SablonAdimi(
                "duzeltme",
                "Geri bildirim ve düzeltme",
                "Firma geri bildirim verdi, düzeltmeler yapıldı.",
                "Geri bildirimi tek listede ve önceliğiyle verin.",
                5,
            ),
            SablonAdimi(
                "son_teslim",
                "Son teslim",
                SON_ADIM_TANIMI,
                "Son teslimi başarı kriterine göre birlikte kontrol edin.",
                6,
            ),
        ),
    ),
    DENEME_ISI: SurecSablonu(
        DENEME_ISI,
        "Deneme işi süreci",
        (
            _TANISMA_TOPLANTISI,
            _ON_GORUSME,
            SablonAdimi(
                "deneme_kapsami",
                "Deneme işinin kapsamı ve ölçütü onaylandı",
                "Deneme işinin süresi, yeri ve başarı ölçütü iki firma tarafından onaylandı.",
                "Deneme işini küçük tutun (tek şube, tek ürün grubu gibi); başarı ölçütünü "
                "ilandaki kritere bağlayın.",
                3,
            ),
            SablonAdimi(
                "deneme_yurutuldu",
                "Deneme işi yürütüldü",
                "Deneme işi planlanan süre boyunca yürütüldü, sonuçlar toplandı.",
                "Ara sonuçları düzenli paylaşın; sorunları beklemeden konuşun.",
                8,
            ),
            SablonAdimi(
                "degerlendirme",
                "Değerlendirme: devam mı?",
                SON_ADIM_TANIMI,
                "Sonuçları başarı ölçütüyle karşılaştırın; devam edilecekse sonraki adımı konuşun.",
                9,
            ),
        ),
    ),
    TEDARIK: SurecSablonu(
        TEDARIK,
        "Tedarik süreci",
        (
            _TANISMA_TOPLANTISI,
            SablonAdimi(
                "teklif",
                "Teklif ve numune",
                "Tedarikçi teklifini ve gerekiyorsa numunesini iletti.",
                "Miktarı, teslim sıklığını ve kalite beklentisini teklif istemeden önce yazın.",
                2,
            ),
            SablonAdimi(
                "anlasma",
                "Anlaşma",
                "Fiyat, miktar ve teslim koşulları üzerinde anlaşıldı.",
                "Koşulları yazılı hale getirin; ilk teslimatın tarihini belirleyin.",
                4,
            ),
            SablonAdimi(
                "ilk_teslimat",
                "İlk teslimat",
                "İlk teslimat yapıldı ve teslim alındı.",
                "Teslimatı kalite beklentisine göre kontrol edin, sorunları hemen bildirin.",
                6,
            ),
            SablonAdimi(
                "degerlendirme",
                "Teslimat değerlendirmesi",
                SON_ADIM_TANIMI,
                "Teslimatları başarı kriterine göre gözden geçirin.",
                8,
            ),
        ),
    ),
    ISBIRLIGI: SurecSablonu(
        ISBIRLIGI,
        "İş birliği süreci",
        (
            _TANISMA_TOPLANTISI,
            _ON_GORUSME,
            SablonAdimi(
                "kapsam",
                "İş birliğinin kapsamı netleşti",
                "Kimin ne yapacağı, süre ve başarı ölçütü iki firma tarafından onaylandı.",
                "Her firmanın sorumluluğunu ayrı ayrı yazın.",
                3,
            ),
            SablonAdimi(
                "yurutme",
                "İş birliği yürütüldü",
                "Kararlaştırılan işler yapıldı, sonuçlar paylaşıldı.",
                "Düzenli kısa toplantılarla ilerlemeyi paylaşın.",
                8,
            ),
            SablonAdimi(
                "degerlendirme",
                "Değerlendirme",
                SON_ADIM_TANIMI,
                "Sonuçları başarı kriteriyle karşılaştırın; devam edip etmeyeceğinizi konuşun.",
                9,
            ),
        ),
    ),
}


def surec_sec(aday_firma: bool, musaitlik: str | None, isbirligi_turu: str | None) -> SurecSablonu:
    """Eşleşmenin türüne göre şablon. Genç ilanında müsaitlik, ortak ilanında iş birliği türü."""
    if aday_firma:
        if isbirligi_turu == "pilot":
            return SABLONLAR[DENEME_ISI]
        if isbirligi_turu == "tedarik":
            return SABLONLAR[TEDARIK]
        return SABLONLAR[ISBIRLIGI]
    if musaitlik == STAJ:
        return SABLONLAR[STAJ_SURECI]
    if musaitlik == PROJE_BAZLI:
        return SABLONLAR[PROJE]
    return SABLONLAR[ISE_ALIM]


def surec_adi(anahtar: str | None) -> str | None:
    """Kayıttaki anahtarın görünen adı; eski kayıtta (anahtar yok) None."""
    sablon = SABLONLAR.get(anahtar or "")
    return sablon.ad if sablon else None


def hedef_tarihi(baslangic: dt.date, hafta: int) -> dt.date:
    return baslangic + dt.timedelta(weeks=hafta)


def sablon_adimlari(sablon: SurecSablonu, baslangic: dt.date) -> list[PlanAdimi]:
    """Şablonun kendi metniyle plan; ajan yoksa ya da başarısızsa bu yazılır."""
    return [
        PlanAdimi(
            anahtar=adim.anahtar,
            baslik=adim.baslik,
            tamam_tanimi=adim.tamam_tanimi,
            oneri=adim.oneri,
            hedef_tarih=hedef_tarihi(baslangic, adim.hafta),
        )
        for adim in sablon.adimlar
    ]
