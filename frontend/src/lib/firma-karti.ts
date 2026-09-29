/**
 * Firma kartı formu: dönüştürme, doğrulama, değişen alanlar ve panel çağrısı
 * (docs/plans/firma-akisi.md § 0 kararlar 3, 9; § 5). Saf fonksiyonlar;
 * testleri firma-karti.test.ts'de. Firmaya "siz".
 *
 * Backend son sözü söyler (app/schemas/firma_karti.py).
 */

import type {
  FirmaKartiGirdisi,
  FirmaKartiTaslagi,
  FirmaKartiYaniti,
  MeYaniti,
} from "@/lib/api";

export const YETKINLIK_EN_COK = 15;
export const NE_YAPIYORUZ_EN_UZUN = 1000;

export type IsbirligiTuru =
  "pilot" | "tedarik" | "ortak_urun" | "yatirim" | "diger";

export const ISBIRLIGI_TURLERI: { deger: IsbirligiTuru; etiket: string }[] = [
  { deger: "pilot", etiket: "Pilot uygulama" },
  { deger: "tedarik", etiket: "Tedarik" },
  { deger: "ortak_urun", etiket: "Ortak ürün" },
  { deger: "yatirim", etiket: "Yatırım" },
  { deger: "diger", etiket: "Diğer" },
];

export function isbirligiTuruEtiketi(tur: string): string {
  return ISBIRLIGI_TURLERI.find((t) => t.deger === tur)?.etiket ?? tur;
}

/** Form alanları: yetkinlikler virgülle ayrılmış tek metin olarak düzenlenir. */
export type FirmaKartiFormu = {
  ne_yapiyoruz: string;
  yetkinlikler: string;
  onceki_isler: string;
  aranan_isbirligi: string;
  isbirligi_turleri: string[];
};

/** Virgül ya da satır sonuyla ayrılmış yetkinlikler; tekrarsız, sırası korunur. */
export function yetkinlikleriAyir(metin: string): string[] {
  const gorulen = new Set<string>();
  const sonuc: string[] = [];
  for (const parca of metin.split(/[,\n]/)) {
    const temiz = parca.trim().replace(/\s+/g, " ");
    const anahtar = temiz.toLocaleLowerCase("tr");
    if (temiz && !gorulen.has(anahtar)) {
      gorulen.add(anahtar);
      sonuc.push(temiz);
    }
  }
  return sonuc;
}

export function kartiForma(
  kart: FirmaKartiYaniti | FirmaKartiTaslagi,
): FirmaKartiFormu {
  return {
    ne_yapiyoruz: kart.ne_yapiyoruz ?? "",
    yetkinlikler: kart.yetkinlikler.join(", "),
    onceki_isler: kart.onceki_isler ?? "",
    aranan_isbirligi: kart.aranan_isbirligi ?? "",
    isbirligi_turleri: [...kart.isbirligi_turleri],
  };
}

export function formuKartaCevir(form: FirmaKartiFormu): FirmaKartiGirdisi {
  const bos = (metin: string) => (metin.trim() ? metin.trim() : null);
  return {
    ne_yapiyoruz: form.ne_yapiyoruz.trim(),
    yetkinlikler: yetkinlikleriAyir(form.yetkinlikler),
    onceki_isler: bos(form.onceki_isler),
    aranan_isbirligi: bos(form.aranan_isbirligi),
    isbirligi_turleri: ISBIRLIGI_TURLERI.map((t) => t.deger).filter((t) =>
      form.isbirligi_turleri.includes(t),
    ),
  };
}

export function kartFormunuDogrula(form: FirmaKartiFormu): string[] {
  const hatalar: string[] = [];
  if (!form.ne_yapiyoruz.trim()) hatalar.push("Firmanızın ne yaptığını yazın.");
  else if (form.ne_yapiyoruz.trim().length > NE_YAPIYORUZ_EN_UZUN)
    hatalar.push(`Açıklama en çok ${NE_YAPIYORUZ_EN_UZUN} karakter olmalı.`);
  const yetkinlikler = yetkinlikleriAyir(form.yetkinlikler);
  if (yetkinlikler.length === 0) hatalar.push("En az bir yetkinlik yazın.");
  else if (yetkinlikler.length > YETKINLIK_EN_COK)
    hatalar.push(`En çok ${YETKINLIK_EN_COK} yetkinlik yazabilirsiniz.`);
  return hatalar;
}

/** PATCH gövdesi: yalnızca değişen alanlar (boşsa gönderilecek bir şey yok). */
export function degisenKartAlanlari(
  kart: FirmaKartiYaniti,
  form: FirmaKartiFormu,
): Partial<FirmaKartiGirdisi> {
  const yeni = formuKartaCevir(form);
  const degisen: Partial<FirmaKartiGirdisi> = {};
  if (yeni.ne_yapiyoruz !== kart.ne_yapiyoruz)
    degisen.ne_yapiyoruz = yeni.ne_yapiyoruz;
  if (yeni.yetkinlikler.join("\n") !== kart.yetkinlikler.join("\n"))
    degisen.yetkinlikler = yeni.yetkinlikler;
  if (yeni.onceki_isler !== kart.onceki_isler)
    degisen.onceki_isler = yeni.onceki_isler;
  if (yeni.aranan_isbirligi !== kart.aranan_isbirligi)
    degisen.aranan_isbirligi = yeni.aranan_isbirligi;
  if (yeni.isbirligi_turleri.join() !== kart.isbirligi_turleri.join())
    degisen.isbirligi_turleri = yeni.isbirligi_turleri;
  return degisen;
}

/**
 * Firma panelindeki çağrı (karar 9): kartı olmayan firma ortak olarak
 * önerilmez. Engellemez; yalnızca genç arayan firma için gerekli değil.
 */
export function firmaKartiCagrisi(hesap: MeYaniti): string | null {
  if (hesap.rol !== "kurum" || hesap.firma_karti_var) return null;
  return "Firma kartınızı oluşturun, diğer firmalar sizi bulabilsin.";
}
