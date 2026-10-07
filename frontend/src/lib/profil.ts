/**
 * Gencin profil formu: doğrulama, dönüştürme ve uyarı bandı kararı
 * (docs/agent-specs.md § 1, docs/kararlar.md G10). Saf fonksiyonlar; testleri
 * profil.test.ts'de. Kayıt sayfası ve profil sayfası aynı formu kullanır.
 *
 * Backend son sözü söyler (app/schemas/profil.py); buradaki kontrol yalnızca
 * kullanıcıya formu göndermeden önce doğru cümleyi göstermek için.
 */

import type {
  GencKayitProfili,
  GencProfil,
  KariyerDurumu,
} from "@/lib/api";

export const SINIF_EN_AZ = 1;
export const SINIF_EN_COK = 8;
export const MEZUNIYET_EN_ESKI = 1950;
const MEZUNIYET_ILERI_YIL = 8;

/** Form alanları metin olarak tutulur (input'lar metin döner). */
export type ProfilFormu = {
  sehir: string;
  calisma_modelleri: string[];
  kariyer_durumu: KariyerDurumu | "";
  musaitlikler: string[];
  musaitlik_baslangici: string;
  okul: string;
  bolum: string;
  sinif: string;
  mezuniyet_yili: string;
  github_url: string;
  linkedin_url: string;
  portfolyo_url: string;
};

export const BOS_PROFIL_FORMU: ProfilFormu = {
  sehir: "",
  calisma_modelleri: [],
  kariyer_durumu: "",
  musaitlikler: [],
  musaitlik_baslangici: "",
  okul: "",
  bolum: "",
  sinif: "",
  mezuniyet_yili: "",
  github_url: "",
  linkedin_url: "",
  portfolyo_url: "",
};

export const EKSIK_ALAN_ETIKETLERI: Record<string, string> = {
  sehir: "şehir",
  calisma_modelleri: "çalışma modeli",
  musaitlikler: "müsaitlik",
  kariyer_durumu: "durum",
};

// Backend şemayı tamamlar (şemasız adrese https:// ekler); burada yalnızca
// açıkça yanlış olanı yakalıyoruz: boşluk ya da noktasız alan adı.
const URL_KALIBI = /^(https?:\/\/)?[^\s/]+\.[^\s/]+(\/\S*)?$/i;

function tamSayi(metin: string): number | null {
  const temiz = metin.trim();
  if (!/^\d+$/.test(temiz)) return null;
  return Number(temiz);
}

/**
 * Çalışma tercihlerinin hataları: eşleştirmenin kullandığı alanlar. Kayıtta
 * profille birlikte, sonra kart sayfasında düzenlenir (docs/kararlar.md G18).
 */
export function tercihHatalari(form: ProfilFormu): string[] {
  const hatalar: string[] = [];
  if (!form.sehir) hatalar.push("Şehir seç.");
  if (form.calisma_modelleri.length === 0)
    hatalar.push("En az bir çalışma modeli işaretle.");
  if (form.musaitlikler.length === 0)
    hatalar.push("En az bir müsaitlik işaretle.");
  return hatalar;
}

/** Hesap bilgilerinin (eğitim, bağlantılar) hataları; Hesabım sayfası. */
export function hesapHatalari(
  form: ProfilFormu,
  buYil: number = new Date().getFullYear(),
): string[] {
  const hatalar: string[] = [];
  if (!form.kariyer_durumu) hatalar.push("Durumunu seç.");

  if (form.sinif.trim()) {
    const sinif = tamSayi(form.sinif);
    if (sinif === null || sinif < SINIF_EN_AZ || sinif > SINIF_EN_COK)
      hatalar.push(`Sınıf ${SINIF_EN_AZ} ile ${SINIF_EN_COK} arasında olmalı.`);
  }
  if (form.mezuniyet_yili.trim()) {
    const yil = tamSayi(form.mezuniyet_yili);
    const ust = buYil + MEZUNIYET_ILERI_YIL;
    if (yil === null || yil < MEZUNIYET_EN_ESKI || yil > ust)
      hatalar.push(
        `Mezuniyet yılı ${MEZUNIYET_EN_ESKI} ile ${ust} arasında olmalı.`,
      );
  }
  for (const [alan, ad] of [
    ["github_url", "GitHub"],
    ["linkedin_url", "LinkedIn"],
    ["portfolyo_url", "Portfolyo"],
  ] as const) {
    const deger = form[alan].trim();
    if (deger && !URL_KALIBI.test(deger))
      hatalar.push(`${ad} adresi geçerli bir web adresi değil.`);
  }
  return hatalar;
}

/** Kayıt formunun hepsi: önce tercihler, sonra hesap bilgileri. */
export function profilFormunuDogrula(
  form: ProfilFormu,
  buYil: number = new Date().getFullYear(),
): string[] {
  return [...tercihHatalari(form), ...hesapHatalari(form, buYil)];
}

function bosIseNull(metin: string): string | null {
  const temiz = metin.trim();
  return temiz ? temiz : null;
}

/** Geçerli formu backend'in beklediği gövdeye çevirir (önce doğrula). */
export function formuProfileCevir(form: ProfilFormu): GencKayitProfili {
  return {
    sehir: form.sehir,
    calisma_modelleri: form.calisma_modelleri,
    kariyer_durumu: form.kariyer_durumu as KariyerDurumu,
    musaitlikler: form.musaitlikler,
    musaitlik_baslangici: bosIseNull(form.musaitlik_baslangici),
    okul: bosIseNull(form.okul),
    bolum: bosIseNull(form.bolum),
    sinif: tamSayi(form.sinif),
    mezuniyet_yili: tamSayi(form.mezuniyet_yili),
    github_url: bosIseNull(form.github_url),
    linkedin_url: bosIseNull(form.linkedin_url),
    portfolyo_url: bosIseNull(form.portfolyo_url),
  };
}

const TERCIH_ALANLARI_GOVDE = [
  "sehir",
  "calisma_modelleri",
  "musaitlikler",
  "musaitlik_baslangici",
] as const;

/** PATCH /profil gövdesi: yalnızca çalışma tercihleri (kart sayfası). */
export function tercihGovdesi(form: ProfilFormu) {
  const tam = formuProfileCevir(form);
  return Object.fromEntries(
    TERCIH_ALANLARI_GOVDE.map((alan) => [alan, tam[alan]]),
  ) as Pick<GencKayitProfili, (typeof TERCIH_ALANLARI_GOVDE)[number]>;
}

/** PATCH /profil gövdesi: tercihler dışındaki her şey (Hesabım). */
export function hesapGovdesi(form: ProfilFormu) {
  const tam: Partial<GencKayitProfili> = { ...formuProfileCevir(form) };
  for (const alan of TERCIH_ALANLARI_GOVDE) delete tam[alan];
  return tam;
}

/** Kayıtlı profili düzenleme formuna çevirir. */
export function profildenForma(profil: GencProfil): ProfilFormu {
  return {
    sehir: profil.sehir ?? "",
    calisma_modelleri: profil.calisma_modelleri,
    kariyer_durumu: profil.kariyer_durumu ?? "",
    musaitlikler: profil.musaitlikler,
    musaitlik_baslangici: profil.musaitlik_baslangici ?? "",
    okul: profil.okul ?? "",
    bolum: profil.bolum ?? "",
    sinif: profil.sinif?.toString() ?? "",
    mezuniyet_yili: profil.mezuniyet_yili?.toString() ?? "",
    github_url: profil.github_url ?? "",
    linkedin_url: profil.linkedin_url ?? "",
    portfolyo_url: profil.portfolyo_url ?? "",
  };
}

/** Eşleştirmenin sert filtreleri; kart onayında profilde yoksa sorulur. */
const FILTRE_ALANLARI = ["sehir", "calisma_modelleri", "musaitlikler"];

/**
 * Kart onay formunda "nerede ve nasıl çalışabilirsin" soruları gösterilsin mi?
 * Kayıtta alındıkları için yalnızca eksikse (bu alanlardan önce açılmış hesap).
 */
export function onaydaProfilSorulmali(eksikAlanlar: string[]): boolean {
  return eksikAlanlar.some((alan) => FILTRE_ALANLARI.includes(alan));
}
