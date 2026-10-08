/**
 * Kanıt parçalarının görünüm mantığı (docs/dogrulama.md § 2, § 3).
 * Saf fonksiyonlar; testleri kanit.test.ts'de.
 */

import type { GuvenSkoru, KanitParcasi } from "@/lib/api";

/** Şeması olmayan linke https:// ekler (genç linki çoğu zaman şemasız yazıyor). */
export function kanitAdresi(url: string): string {
  return /^https?:\/\//i.test(url) ? url : `https://${url.replace(/^\/+/, "")}`;
}

/** Link türündeki, adresi olan parçalar (eklenme sırasıyla). */
export function kanitLinkleri(
  kanitlar: KanitParcasi[],
): (KanitParcasi & { url: string })[] {
  return kanitlar.filter(
    (parca): parca is KanitParcasi & { url: string } =>
      parca.tur === "link" && Boolean(parca.url),
  );
}

/**
 * Çalışma değerlendirildi mi? Kanıt, Sonuç ya da Rol'den biri doluysa evet.
 * Yalnızca Referans doluysa (linksiz kalemde referans yanıt verdi) hayır:
 * kanıt henüz değerlendirilmedi.
 */
export function degerlendirildiMi(
  skor: GuvenSkoru | null | undefined,
): boolean {
  if (!skor) return false;
  return [
    skor.kanit_orijinalligi,
    skor.sonuc_olculebilirligi,
    skor.rol_netligi,
  ].some((deger) => deger !== null);
}

/** Yüklenen dosya ve görsel parçaları (eklenme sırasıyla). */
export function dosyaParcalari(kanitlar: KanitParcasi[]): KanitParcasi[] {
  return kanitlar.filter(
    (parca) => parca.tur === "dosya" || parca.tur === "gorsel",
  );
}

/** Dosya boyutu: "340 KB", "1,2 MB". */
export function dosyaBoyutu(bayt: number | null | undefined): string | null {
  if (bayt == null) return null;
  if (bayt < 1024 * 1024) return `${Math.max(1, Math.round(bayt / 1024))} KB`;
  return `${(bayt / (1024 * 1024)).toFixed(1).replace(".", ",")} MB`;
}

/** Dosya seçme kutusunun kabul ettiği türler (backend: core/dosya_hatti.py). */
export const KABUL_EDILEN_DOSYALAR =
  ".pdf,.png,.jpg,.jpeg,.webp,.heic,application/pdf,image/png,image/jpeg,image/webp,image/heic";

export type SecenekKutusu = {
  mesaj: string;
  secenekler: string[];
  /** "Hesabını bağla" önerisi profildeki bölüme gider. */
  hesapBagla: boolean;
};

function googleMu(parca: KanitParcasi): boolean {
  return (
    parca.platform === "google" ||
    /(^|\/\/|\.)(drive|docs)\.google\.com/i.test(parca.url ?? "")
  );
}

/**
 * Okunamayan link için gence gösterilen açıklama ve seçenekler
 * (docs/dogrulama.md § 3). Okunan ya da henüz okunmamış
 * linkte null.
 */
export function okunamayanSecenekleri(
  parca: KanitParcasi,
): SecenekKutusu | null {
  if (parca.tur !== "link") return null;
  switch (parca.erisim) {
    case "giris_gerekli":
      return googleMu(parca)
        ? {
            mesaj:
              "Paylaşım ayarını “Bağlantıya sahip olan herkes” yaparsan içeriğini okuyabiliriz.",
            secenekler: [
              "Paylaşımı açıp linki yeniden ekle",
              "PDF olarak yükle",
              "Referans ekle",
            ],
            hesapBagla: false,
          }
        : {
            mesaj:
              "Bu link yalnızca giriş yapanlara açık; içeriğini göremedik.",
            secenekler: [
              "Herkese açık bir link ekle",
              "PDF olarak yükle",
              "Ekran görüntüsü ekle",
              "Referans ekle",
            ],
            hesapBagla: false,
          };
    case "engellendi":
      return {
        mesaj: "Bu siteye otomatik olarak ulaşamadık; senin hatan değil.",
        secenekler: ["PDF olarak yükle", "Görsel ekle", "Referans ekle"],
        hesapBagla: true,
      };
    case "icerik_yok":
      return {
        mesaj: "Sayfa açıldı ama içeriği okunamadı.",
        secenekler: [
          "Kaynak kod linki ekle",
          "Ekran görüntüsü ekle",
          "Referans ekle",
        ],
        hesapBagla: false,
      };
    case "bulunamadi":
      return {
        mesaj: "Bu adreste bir sayfa yok.",
        secenekler: ["Linki düzelt", "PDF olarak yükle", "Referans ekle"],
        hesapBagla: false,
      };
    default:
      return null;
  }
}

/** e-Devlet belgesinin GİRVAK incelemesi, gencin göreceği cümle. */
export function girvakIncelemesiMetni(
  durum: string | null | undefined,
): string | null {
  if (durum === "bekliyor") return "e-Devlet belgen GİRVAK’ın incelemesinde.";
  if (durum === "onaylandi") return "GİRVAK e-Devlet belgeni doğruladı.";
  if (durum === "reddedildi")
    return "GİRVAK e-Devlet belgeni doğrulayamadı. Barkodun okunaklı olduğu bir kopyasını yükleyebilirsin.";
  return null;
}
