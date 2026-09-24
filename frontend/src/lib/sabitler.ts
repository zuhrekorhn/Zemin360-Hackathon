/**
 * Şehir listesi ve ortak Türkçe etiketler.
 *
 * Şehir serbest metin değil: Eşleştirme'nin tek sert filtresi şehir ve
 * Türkçe'de yazım farkı ("istanbul" / "İstanbul") eşleşmeyi sessizce
 * bozuyor (bkz. backend/app/core/sehir.py). Liste iki tarafta da aynı
 * değerleri üretsin diye buradan geliyor.
 */

/**
 * Çalışma modeli — konumdan AYRI bir alan (LinkedIn/Kariyer.net deseni).
 * Müsaitlik ise çalışma tipi (tam/yarı zamanlı); ikisi karıştırılmamalı.
 */
export const CALISMA_MODELI_ETIKETLERI: Record<string, string> = {
  is_yerinde: "İş yerinde",
  hibrit: "Hibrit",
  uzaktan: "Uzaktan",
};

export const CALISMA_MODELLERI = Object.entries(CALISMA_MODELI_ETIKETLERI).map(
  ([deger, etiket]) => ({ deger, etiket }),
);

export const SEHIRLER = [
  "Adana",
  "Adıyaman",
  "Afyonkarahisar",
  "Ağrı",
  "Aksaray",
  "Amasya",
  "Ankara",
  "Antalya",
  "Ardahan",
  "Artvin",
  "Aydın",
  "Balıkesir",
  "Bartın",
  "Batman",
  "Bayburt",
  "Bilecik",
  "Bingöl",
  "Bitlis",
  "Bolu",
  "Burdur",
  "Bursa",
  "Çanakkale",
  "Çankırı",
  "Çorum",
  "Denizli",
  "Diyarbakır",
  "Düzce",
  "Edirne",
  "Elazığ",
  "Erzincan",
  "Erzurum",
  "Eskişehir",
  "Gaziantep",
  "Giresun",
  "Gümüşhane",
  "Hakkâri",
  "Hatay",
  "Iğdır",
  "Isparta",
  "İstanbul",
  "İzmir",
  "Kahramanmaraş",
  "Karabük",
  "Karaman",
  "Kars",
  "Kastamonu",
  "Kayseri",
  "Kırıkkale",
  "Kırklareli",
  "Kırşehir",
  "Kilis",
  "Kocaeli",
  "Konya",
  "Kütahya",
  "Malatya",
  "Manisa",
  "Mardin",
  "Mersin",
  "Muğla",
  "Muş",
  "Nevşehir",
  "Niğde",
  "Ordu",
  "Osmaniye",
  "Rize",
  "Sakarya",
  "Samsun",
  "Siirt",
  "Sinop",
  "Sivas",
  "Şanlıurfa",
  "Şırnak",
  "Tekirdağ",
  "Tokat",
  "Trabzon",
  "Tunceli",
  "Uşak",
  "Van",
  "Yalova",
  "Yozgat",
  "Zonguldak",
] as const;

/** Açılır liste: yalnızca iller. "Uzaktan" burada değil, çalışma modelinde. */
export const SEHIR_SECENEKLERI = [
  { deger: "", etiket: "Seçiniz" },
  ...SEHIRLER.map((sehir) => ({ deger: sehir, etiket: sehir })),
];

/**
 * Veritabanındaki kod değerlerinin Türkçe karşılıkları.
 *
 * Ekranda "baslangic" değil "Başlangıç" yazmalı; kod değerleri şemanın
 * iç işi. Tek yerden geldikleri için taslak, kart ve öneri ekranları
 * aynı kelimeyi kullanıyor.
 */
export const DENEYIM_ETIKETLERI: Record<string, string> = {
  potansiyel: "Potansiyel",
  baslangic: "Başlangıç",
  orta: "Orta",
  ileri: "İleri",
};

export const MUSAITLIK_ETIKETLERI: Record<string, string> = {
  tam_zamanli: "Tam zamanlı",
  yarim_zamanli: "Yarı zamanlı",
  proje_bazli: "Proje bazlı",
  staj: "Staj",
};

/** Açılır listeler için: boş seçenek + etiketli değerler. */
export const MUSAITLIK_SECENEKLERI = [
  { deger: "", etiket: "Belirtmek istemiyorum" },
  ...Object.entries(MUSAITLIK_ETIKETLERI).map(([deger, etiket]) => ({
    deger,
    etiket,
  })),
];

/**
 * Bilinmeyen bir kod geldiğinde onu gizlemiyoruz: ham değeri göstermek,
 * boş bırakmaktan iyi (şema büyürse fark edelim).
 */
export function etiketle(
  sozluk: Record<string, string>,
  deger: string | null | undefined,
): string {
  if (!deger) return "—";
  return sozluk[deger] ?? deger;
}

/** Şehir zaten kanonik yazımda saklanıyor; boşsa tire. */
export function sehirEtiketi(sehir: string | null | undefined): string {
  return sehir || "—";
}
