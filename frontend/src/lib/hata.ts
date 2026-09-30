import { ApiHatasi } from "@/lib/api";

/** Ekranda gösterilecek hata. `kota` true ise dil modeli hız sınırına takılmış (429). */
export type Hata = { metin: string; kota: boolean };

/**
 * Backend gövde göndermediğinde (ya da gövde okunamadığında) kullanılan
 * cümleler. Backend'in kendi cümleleri (app/core/hatalar.py) bunlarla aynı
 * ayrımı yapıyor ve öncelikli: ne olduğunu en iyi o biliyor.
 *
 * İkisi farklı şey söylüyor, karıştırılmamalı:
 *   429 — hız sınırı: dil modeli o an çok fazla istek alıyor.
 *   503 — sağlayıcı arızası ya da zaman aşımı; model yanıt veremedi.
 */
// Hitapsız: genç ve firma aynı cümleyi görür (docs/icerik-rehberi.md § 3, § 5.4);
// "tekrar dene" eylemi hata kutusunun düğmesinde, görüntüleyenin hitabıyla.
export const HIZ_SINIRI_MESAJI =
  "Şu an çok yoğunuz, isteğe yanıt veremedik. Biraz sonra yeniden denenebilir.";
export const MESGUL_MESAJI =
  "Şu an yanıt veremedik. Birkaç saniye sonra yeniden denenebilir.";
const BEKLENMEYEN_MESAJ = "Beklenmeyen bir sorun oldu, isteği tamamlayamadık.";
export const BAGLANTI_MESAJI = "Şu an bağlantı kuramadık.";
/** Backend cümle göndermediğinde durum koduna göre (teknik kod gösterilmez). */
const DURUM_MESAJLARI: Record<number, string> = {
  401: "Oturumun süresi dolmuş; yeniden giriş gerekiyor.",
  403: "Bu işlem bu hesap türü için değil.",
  404: "Aranan kayıt bulunamadı.",
  409: "Bu işlem şu an yapılamıyor; sayfa güncel olmayabilir.",
  422: "Bazı alanlar eksik ya da hatalı.",
};

/**
 * Aynı isteği tekrarlamak sonucu değiştirir mi?
 *
 * 404 (yok) ve 409 (durum uygun değil) kalıcı: tekrar denemek aynı yanıtı
 * getirir. Ağ hatası, 429 ve 5xx geçici.
 */
export function tekrarDenenebilirMi(sebep: unknown): boolean {
  if (sebep instanceof ApiHatasi && sebep.durumKodu !== undefined) {
    return sebep.durumKodu !== 404 && sebep.durumKodu !== 409;
  }
  return true;
}

/**
 * Hatayı kullanıcıya söylenebilir bir cümleye çevirir — uygulamadaki tek yer.
 *
 * Backend `{"detail": "..."}` gönderdiyse o cümle gösterilir — ne olduğunu
 * en iyi o biliyor. Yoksa durum koduna göre yedek cümle.
 */
export function hatayaCevir(sebep: unknown): Hata {
  if (!(sebep instanceof ApiHatasi)) {
    return { metin: BEKLENMEYEN_MESAJ, kota: false };
  }
  // Ağ hatası: durum kodu yok.
  if (sebep.durumKodu === undefined)
    return { metin: BAGLANTI_MESAJI, kota: false };

  const kota = sebep.durumKodu === 429;
  if (sebep.ayrinti) return { metin: sebep.ayrinti, kota };
  if (sebep.durumKodu === 429) return { metin: HIZ_SINIRI_MESAJI, kota };
  if (sebep.durumKodu === 503) return { metin: MESGUL_MESAJI, kota };
  return { metin: DURUM_MESAJLARI[sebep.durumKodu] ?? BEKLENMEYEN_MESAJ, kota };
}
