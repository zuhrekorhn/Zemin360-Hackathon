/**
 * Hesap bağlamanın metinleri (docs/plans/dogrulama-iyilestirme.md § 6).
 * Saf fonksiyonlar; testleri hesap-baglama.test.ts'de. Gence "sen".
 *
 * Bağlı hesaptaki çalışma daha güçlü bir kanıt sayılır: çalışmanın sana ait
 * olduğunu platform gösterir. Sıralama: önce OAuth (tek tık), sonra doğrulama
 * kodu.
 */

type PlatformBilgisi = {
  ad: string;
  /** Profil adresi alanının yer tutucusu. */
  ornek?: string;
  /** "Kodu … ekle" cümlesinin yeri. */
  kodYeri?: string;
};

const PLATFORMLAR: Record<string, PlatformBilgisi> = {
  github: { ad: "GitHub" },
  gitlab: { ad: "GitLab" },
  orcid: { ad: "ORCID" },
  youtube: {
    ad: "YouTube",
    ornek: "ör. youtube.com/@kanalin",
    kodYeri: "YouTube kanal açıklamana",
  },
  kaggle: {
    ad: "Kaggle",
    ornek: "ör. kaggle.com/kullaniciadin",
    kodYeri: "Kaggle profilindeki kısa tanıtıma (bio)",
  },
  behance: {
    ad: "Behance",
    ornek: "ör. behance.net/kullaniciadin",
    kodYeri: "Behance profilindeki tanıtım yazısına",
  },
  dribbble: {
    ad: "Dribbble",
    ornek: "ör. dribbble.com/kullaniciadin",
    kodYeri: "Dribbble profilindeki tanıtım yazısına",
  },
  medium: {
    ad: "Medium",
    ornek: "ör. medium.com/@kullaniciadin",
    kodYeri: "Medium profilindeki kısa tanıtıma (bio)",
  },
  vimeo: {
    ad: "Vimeo",
    ornek: "ör. vimeo.com/kullaniciadin",
    kodYeri: "Vimeo profilindeki tanıtım yazısına",
  },
  soundcloud: {
    ad: "SoundCloud",
    ornek: "ör. soundcloud.com/kullaniciadin",
    kodYeri: "SoundCloud profilindeki tanıtım yazısına",
  },
  kisisel_site: {
    ad: "Kişisel site",
    ornek: "ör. adin.dev",
    kodYeri: "sitenin ana sayfasına (görünür bir yere)",
  },
};

export function platformAdi(platform: string): string {
  return PLATFORMLAR[platform]?.ad ?? platform;
}

export function profilOrnegi(platform: string): string {
  return PLATFORMLAR[platform]?.ornek ?? "Hesabının adresi";
}

/** Kodun nereye yazılacağını söyleyen cümle. */
export function kodYonergesi(platform: string, kod: string): string {
  const yer = PLATFORMLAR[platform]?.kodYeri ?? "hesabının açıklamasına";
  return `${kod} kodunu ${yer} ekle ve kaydet, sonra "Kodu kontrol et"e bas. Bağlandıktan sonra kodu silebilirsin.`;
}

const YONTEMLER: Record<string, string> = {
  oauth: "Giriş yaparak bağlandı",
  profil_kodu: "Doğrulama koduyla bağlandı",
  elle: "GİRVAK doğruladı",
};

export function yontemEtiketi(yontem: string): string {
  return YONTEMLER[yontem] ?? "Bağlı";
}

/** "47 saat daha geçerli" / "1 saatten az kaldı" / null (süresi doldu). */
export function kalanSure(sonGecerlilik: string, simdi: Date): string | null {
  const kalanMs = new Date(sonGecerlilik).getTime() - simdi.getTime();
  if (kalanMs <= 0) return null;
  const saat = Math.floor(kalanMs / 3_600_000);
  return saat < 1 ? "1 saatten az kaldı" : `${saat} saat daha geçerli`;
}
