/**
 * GİRVAK gözlem paneli görünüm kuralları (docs/dogrulama.md § 10.3).
 * Sayılar backend'den gelir (`GET /girvak/gozlem`); burada yalnızca "ekranda ne
 * yazsın". Testleri gozlem.test.ts'de.
 */

import type { ServisDurumu } from "@/lib/api";

export const GOZLEM_GUNLERI = [7, 30, 90] as const;

const ERISIM_ETIKETLERI: Record<string, string> = {
  acik: "Açık",
  giris_gerekli: "Giriş istiyor",
  engellendi: "Engelledi",
  icerik_yok: "İçerik yok",
  bulunamadi: "Bulunamadı",
  guvensiz: "Güvenli değil",
  hata: "Okunamadı",
};

export function erisimEtiketi(erisim: string): string {
  return ERISIM_ETIKETLERI[erisim] ?? erisim;
}

const PLATFORM_ETIKETLERI: Record<string, string> = {
  web: "Diğer siteler",
  github: "GitHub",
  gitlab: "GitLab",
  youtube: "YouTube",
  medium: "Medium",
  behance: "Behance",
  dribbble: "Dribbble",
  kaggle: "Kaggle",
  google: "Google belgeleri",
};

export function platformEtiketi(platform: string): string {
  return PLATFORM_ETIKETLERI[platform] ?? platform;
}

const SERVIS_ETIKETLERI: Record<string, string> = {
  eposta: "E-posta",
  oauth: "Hesap bağlama",
  depo: "Dosya deposu",
  virus: "Virüs taraması",
  yedek_okuyucu: "Yedek okuyucu",
  uzak_okuyucu: "Uzak okuyucu",
  gorsel_arayici: "Görsel arama",
};

export function servisEtiketi(servis: string): string {
  return SERVIS_ETIKETLERI[servis] ?? servis;
}

/** Açık oranı "%80" olarak. */
export function yuzdeYaz(oran: number): string {
  return `%${Math.round(oran * 100)}`;
}

/** Süre, okunur birimle: 850 ms, 3,2 sn. */
export function sureYaz(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toLocaleString("tr-TR", { maximumFractionDigits: 1 })} sn`;
}

export type ServisOzeti = { etiket: string; sorunlu: boolean };

/**
 * Servisin durumu tek etiketle. Sıra: kapalıysa kapalı; son çağrı hataysa
 * (son hata, son başarıdan yeni) sorunlu; çağrı varsa çalışıyor; yoksa henüz
 * çağrılmadı. "Kapalı" bilinçli bir ayardır, sorun sayılmaz.
 */
export function servisOzeti(s: ServisDurumu): ServisOzeti {
  if (s.kip === "kapali") return { etiket: "Kapalı", sorunlu: false };
  const sonHataYeni =
    s.son_hata !== null &&
    (s.son_basari === null ||
      new Date(s.son_hata).getTime() > new Date(s.son_basari).getTime());
  if (sonHataYeni) return { etiket: "Son çağrı hatalı", sorunlu: true };
  if (s.basari_sayisi + s.hata_sayisi > 0)
    return { etiket: "Çalışıyor", sorunlu: false };
  return { etiket: "Henüz çağrılmadı", sorunlu: false };
}

/** "12 başarılı · 1 hatalı" */
export function servisSayilari(s: ServisDurumu): string {
  return `${s.basari_sayisi} başarılı · ${s.hata_sayisi} hatalı`;
}
