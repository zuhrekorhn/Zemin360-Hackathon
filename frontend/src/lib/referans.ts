import type {
  FormCevabi,
  ReferansDurumu,
  ReferansIliskisi,
  ReferansIstegiBilgisi,
} from "@/lib/api";

/**
 * Referans formunun ve referans satırının metinleri
 * (docs/dogrulama.md § 7). Sayfa ve kanıt bölümü aynı
 * etiketleri buradan alır; değer kümeleri backend'deki şemayla aynı.
 */

export const ILISKI_SECENEKLERI: { deger: ReferansIliskisi; etiket: string }[] =
  [
    { deger: "yonetici", etiket: "Yöneticisiydim" },
    { deger: "takim_arkadasi", etiket: "Takım arkadaşıydım" },
    { deger: "ogretmen_danisman", etiket: "Öğretmeni ya da danışmanıydım" },
    { deger: "musteri", etiket: "Müşterisiydim" },
    { deger: "diger", etiket: "Başka bir yerden" },
  ];

export const CEVAP_SECENEKLERI: { deger: FormCevabi; etiket: string }[] = [
  { deger: "evet", etiket: "Evet" },
  { deger: "kismen", etiket: "Kısmen" },
  { deger: "hayir", etiket: "Hayır" },
  { deger: "bilmiyorum", etiket: "Bilmiyorum" },
];

/** Gencin gördüğü kısa ilişki adı. */
const ILISKI_ADLARI: Record<ReferansIliskisi, string> = {
  yonetici: "yönetici",
  takim_arkadasi: "takım arkadaşı",
  ogretmen_danisman: "öğretmen / danışman",
  musteri: "müşteri",
  diger: "diğer",
};

const CEVAP_ADLARI: Record<FormCevabi, string> = {
  evet: "evet",
  kismen: "kısmen",
  hayir: "hayır",
  bilmiyorum: "bilmiyorum",
};

export const REFERANS_DURUMLARI: Record<string, string> = {
  bekliyor: "Yanıt bekleniyor",
  yanitlandi: "Yanıtladı",
  yanit_yok: "Süresinde yanıt gelmedi",
  geri_cekildi: "Geri çekildi",
};

const GUC_ETIKETLERI: Record<string, string> = {
  kurumsal_eposta: "Kurumsal e-posta",
  egitim_eposta: "Eğitim kurumu e-postası",
};

/**
 * Referans satırının özeti: hangi soruya ne dedi, ilişki ve güç işaretleri.
 * Puan değil: Referans başlığını backend hesaplar, burada yalnızca yanıt görünür.
 */
export function referansOzeti(referans: ReferansDurumu): {
  yanitlar: string[];
  isaretler: string[];
} {
  const yanitlar: string[] = [];
  const sorular: [string, FormCevabi | null][] = [
    ["Çalışma", referans.iddia_dogru],
    ["Pay", referans.pay_dogru],
    ["Sonuç", referans.sonuc_dogru],
  ];
  for (const [ad, cevap] of sorular) {
    if (cevap) yanitlar.push(`${ad}: ${CEVAP_ADLARI[cevap]}`);
  }
  // Eski formun 1-5 yanıtı (dört soruluk formdan önce).
  if (yanitlar.length === 0 && referans.puan !== null) {
    yanitlar.push(`${referans.puan}/5`);
  }

  const isaretler: string[] = [];
  if (referans.iliski) isaretler.push(ILISKI_ADLARI[referans.iliski]);
  if (referans.guc)
    isaretler.push(GUC_ETIKETLERI[referans.guc] ?? referans.guc);
  return { yanitlar, isaretler };
}

export type FormSorusu = {
  alan: "iddia_dogru" | "pay_dogru" | "sonuc_dogru";
  soru: string;
  /** Sorunun altında ayrı satırda gösterilen iddia (pay ya da sonuç). */
  ayrinti: string | null;
};

/** Formdaki sorular: kalemde yazılmamış pay ya da sonuç sorulmaz. */
export function formSorulari(
  bilgi: Pick<ReferansIstegiBilgisi, "pay" | "sonuc">,
): FormSorusu[] {
  const sorular: FormSorusu[] = [
    {
      alan: "iddia_dogru",
      soru: "Çalışma anlatıldığı gibi mi?",
      ayrinti: null,
    },
  ];
  if (bilgi.pay?.trim()) {
    sorular.push({
      alan: "pay_dogru",
      soru: "Payı doğru mu?",
      ayrinti: bilgi.pay,
    });
  }
  if (bilgi.sonuc?.trim()) {
    sorular.push({
      alan: "sonuc_dogru",
      soru: "Sonucu doğru mu?",
      ayrinti: bilgi.sonuc,
    });
  }
  return sorular;
}
