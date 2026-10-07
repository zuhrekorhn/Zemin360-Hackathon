/**
 * Firmanın profil formu: doğrulama, dönüştürme ve uyarı bandı kararı
 * (docs/kararlar.md F1-2, 9). Saf fonksiyonlar; testleri
 * firma-profil.test.ts'de. Kayıt sayfası ve /kurum/profil aynı formu kullanır.
 *
 * Backend son sözü söyler (app/schemas/profil.py); buradaki kontrol yalnızca
 * formu göndermeden önce doğru cümleyi göstermek için. Firmaya "siz".
 */

import type {
  CalisanAraligi,
  FirmaKayitProfili,
  FirmaProfil,
  FirmaTuru,
  MeYaniti,
} from "@/lib/api";

export const KURULUS_EN_ESKI = 1900;
export const TANITIM_EN_UZUN = 300;

export const FIRMA_TURLERI: { deger: FirmaTuru; etiket: string }[] = [
  { deger: "girisim", etiket: "Girişim" },
  { deger: "kobi", etiket: "KOBİ" },
  { deger: "kurumsal", etiket: "Kurumsal" },
];

export const CALISAN_ARALIKLARI: CalisanAraligi[] = [
  "1-10",
  "11-50",
  "51-250",
  "250+",
];

export type FirmaProfilFormu = {
  tur: FirmaTuru | "";
  sektor: string;
  sehir: string;
  web_sitesi: string;
  calisan_araligi: CalisanAraligi | "";
  kurulus_yili: string;
  tanitim: string;
  yetkili_ad: string;
  yetkili_gorev: string;
};

export const BOS_FIRMA_FORMU: FirmaProfilFormu = {
  tur: "",
  sektor: "",
  sehir: "",
  web_sitesi: "",
  calisan_araligi: "",
  kurulus_yili: "",
  tanitim: "",
  yetkili_ad: "",
  yetkili_gorev: "",
};

export const FIRMA_EKSIK_ALAN_ETIKETLERI: Record<string, string> = {
  tur: "firma türü",
  sektor: "sektör",
  sehir: "şehir",
};

// Backend şemayı tamamlar (şemasız adrese https:// ekler).
const URL_KALIBI = /^(https?:\/\/)?[^\s/]+\.[^\s/]+(\/\S*)?$/i;

function tamSayi(metin: string): number | null {
  const temiz = metin.trim();
  if (!/^\d+$/.test(temiz)) return null;
  return Number(temiz);
}

function bosIseNull(metin: string): string | null {
  const temiz = metin.trim();
  return temiz ? temiz : null;
}

/** Gönderilmeden önce gösterilecek hatalar; boşsa form geçerli. */
export function firmaFormunuDogrula(
  form: FirmaProfilFormu,
  buYil: number = new Date().getFullYear(),
): string[] {
  const hatalar: string[] = [];
  if (!form.tur) hatalar.push("Firma türünü seçin.");
  if (!form.sektor.trim()) hatalar.push("Sektörü yazın.");
  if (!form.sehir) hatalar.push("Şehri seçin.");
  const site = form.web_sitesi.trim();
  if (site && !URL_KALIBI.test(site))
    hatalar.push("Web sitesi geçerli bir adres değil.");
  if (form.kurulus_yili.trim()) {
    const yil = tamSayi(form.kurulus_yili);
    if (yil === null || yil < KURULUS_EN_ESKI || yil > buYil)
      hatalar.push(
        `Kuruluş yılı ${KURULUS_EN_ESKI} ile ${buYil} arasında olmalı.`,
      );
  }
  if (form.tanitim.trim().length > TANITIM_EN_UZUN)
    hatalar.push(`Tanıtım en çok ${TANITIM_EN_UZUN} karakter olmalı.`);
  return hatalar;
}

/** Geçerli formu backend'in beklediği gövdeye çevirir (önce doğrula). */
export function formuFirmaProfilineCevir(
  form: FirmaProfilFormu,
): FirmaKayitProfili {
  return {
    tur: form.tur as FirmaTuru,
    sektor: form.sektor.trim(),
    sehir: form.sehir,
    web_sitesi: bosIseNull(form.web_sitesi),
    calisan_araligi: form.calisan_araligi || null,
    kurulus_yili: tamSayi(form.kurulus_yili),
    tanitim: bosIseNull(form.tanitim),
    yetkili_ad: bosIseNull(form.yetkili_ad),
    yetkili_gorev: bosIseNull(form.yetkili_gorev),
  };
}

/** Kayıtlı profili düzenleme formuna çevirir. */
export function firmaProfilindenForma(profil: FirmaProfil): FirmaProfilFormu {
  return {
    tur: profil.tur ?? "",
    sektor: profil.sektor ?? "",
    sehir: profil.sehir ?? "",
    web_sitesi: profil.web_sitesi ?? "",
    calisan_araligi: profil.calisan_araligi ?? "",
    kurulus_yili: profil.kurulus_yili?.toString() ?? "",
    tanitim: profil.tanitim ?? "",
    yetkili_ad: profil.yetkili_ad ?? "",
    yetkili_gorev: profil.yetkili_gorev ?? "",
  };
}

/**
 * Firma panelinin üstündeki engellemeyen bant: bu alanlardan önce açılmış
 * firma hesapları için (docs/kararlar.md F9). Gösterilecek bir şey yoksa null.
 */
export function firmaProfilBandi(hesap: MeYaniti): string | null {
  if (hesap.rol !== "kurum") return null;
  const eksikler = hesap.eksik_profil_alanlari.map(
    (alan) => FIRMA_EKSIK_ALAN_ETIKETLERI[alan] ?? alan,
  );
  const parcalar: string[] = [];
  if (eksikler.length > 0)
    parcalar.push(`profilinizde eksik bilgi var (${eksikler.join(", ")})`);
  if (!hesap.kvkk_onayli)
    parcalar.push("KVKK aydınlatma metnini onaylamadınız");
  if (parcalar.length === 0) return null;
  return `Profilinizi tamamlayın: ${parcalar.join("; ")}.`;
}

/**
 * İhtiyaç onay formunda firmanın sektörü ve şehri sorulsun mu? Kayıtta
 * alındıkları için yalnızca eksikse (bu alanlardan önce açılmış hesap).
 */
export function onaydaFirmaBilgisiSorulmali(eksikAlanlar: string[]): boolean {
  return eksikAlanlar.includes("sektor") || eksikAlanlar.includes("sehir");
}
