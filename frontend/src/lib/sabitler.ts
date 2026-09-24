/**
 * Şehir listesi ve ortak Türkçe etiketler.
 *
 * Şehir serbest metin değil: Eşleştirme'nin tek sert filtresi şehir ve
 * Türkçe'de yazım farkı ("istanbul" / "İstanbul") eşleşmeyi sessizce
 * bozuyor (bkz. backend/app/core/sehir.py). Liste iki tarafta da aynı
 * değerleri üretsin diye buradan geliyor.
 */

export const UZAKTAN = "uzaktan";

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

/** Açılır listede gösterilen seçenekler — "fark etmez" en başta. */
export const SEHIR_SECENEKLERI = [
  { deger: "", etiket: "Belirtmek istemiyorum" },
  { deger: UZAKTAN, etiket: "Uzaktan / fark etmez" },
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

/** Şehir alanı "uzaktan" ise ekranda kod değil cümle görünsün. */
export function sehirEtiketi(sehir: string | null | undefined): string {
  if (!sehir) return "—";
  return sehir === UZAKTAN ? "Uzaktan / fark etmez" : sehir;
}
