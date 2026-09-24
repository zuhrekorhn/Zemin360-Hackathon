import { ApiHatasi } from "@/lib/api";

/** Ekranda gösterilecek hata. `kota` true ise sorun geçici, tekrar denenebilir. */
export type Hata = { metin: string; kota: boolean };

/**
 * Hatayı kullanıcıya söylenebilir bir cümleye çevirir.
 *
 * 429 ayrı tutuluyor: Gemini'nin günlük kotası dolduğunda kullanıcı bir şeyi
 * yanlış yapmış değil, biraz sonra tekrar denemesi yeterli.
 */
export function hatayaCevir(sebep: unknown): Hata {
  if (sebep instanceof ApiHatasi && sebep.durumKodu === 429) {
    return {
      metin: "Şu an yoğunluk var. Birkaç saniye sonra tekrar dene.",
      kota: true,
    };
  }
  return {
    metin:
      sebep instanceof ApiHatasi
        ? sebep.message
        : "Beklenmeyen bir şey oldu, tekrar dene.",
    kota: false,
  };
}
