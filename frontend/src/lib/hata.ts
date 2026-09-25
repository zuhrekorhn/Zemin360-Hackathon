import { ApiHatasi } from "@/lib/api";

/** Ekranda gösterilecek hata. `kota` true ise dil modelinin kotası dolmuş. */
export type Hata = { metin: string; kota: boolean };

/**
 * Backend gövde göndermediğinde (ya da gövde okunamadığında) kullanılan
 * cümleler. Backend'in kendi cümleleri (app/core/hatalar.py) bunlarla aynı
 * ayrımı yapıyor ve öncelikli: ne olduğunu en iyi o biliyor.
 *
 * İkisi farklı şey söylüyor, karıştırılmamalı:
 *   429 — günlük kota doldu; saatler sürebilir.
 *   503 — model anlık yoğun; saniyeler içinde geçer.
 */
export const KOTA_MESAJI = "Dil modeli kotası doldu. Bir süre sonra tekrar dene.";
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
 * Backend `{"detail": "..."}` gönderdiyse o cümle gösterilir. Önceden 429
 * burada "yoğunluk var, birkaç saniye sonra dene" diye eziliyordu; oysa 429
 * günlük kota demek ve kullanıcı saniyeler sonra yine aynı hatayı görüyordu.
 */
export function hatayaCevir(sebep: unknown): Hata {
  if (!(sebep instanceof ApiHatasi)) {
    return { metin: BEKLENMEYEN_MESAJ, kota: false };
  }

  const kota = sebep.durumKodu === 429;
  if (sebep.ayrinti) return { metin: sebep.ayrinti, kota };
  if (sebep.durumKodu === 429) return { metin: KOTA_MESAJI, kota };
  if (sebep.durumKodu === 503) return { metin: MESGUL_MESAJI, kota };
  return { metin: sebep.message, kota };
}
