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
export const HIZ_SINIRI_MESAJI =
  "Dil modeli şu an çok fazla istek alıyor. Biraz sonra tekrar dene.";
export const MESGUL_MESAJI =
  "Dil modeli şu an yoğun. Birkaç saniye sonra tekrar dene.";
const BEKLENMEYEN_MESAJ = "Beklenmeyen bir şey oldu, tekrar dene.";

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

  const kota = sebep.durumKodu === 429;
  if (sebep.ayrinti) return { metin: sebep.ayrinti, kota };
  if (sebep.durumKodu === 429) return { metin: HIZ_SINIRI_MESAJI, kota };
  if (sebep.durumKodu === 503) return { metin: MESGUL_MESAJI, kota };
  return { metin: sebep.message, kota };
}
