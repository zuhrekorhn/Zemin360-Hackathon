/**
 * Bilinçli çıkışın izi. "Çıkış"a basınca oturum silinir ve ana sayfaya gidilir;
 * ama o sırada açık olan sayfanın giriş kapısı oturumun kapandığını görüp
 * `/giris?sonra=<o sayfa>`'ya yönlendiriyordu. Sonraki girişte (başka bir
 * hesap bile olsa) öncekinin sayfası açılıyordu. Kapı bu kısa pencerede
 * "sonra" yazmaz. Saf; testi cikis.test.ts'de.
 */

/** Çıkıştan sonra ana sayfaya geçişin bitmesi için yeterli süre. */
export const CIKIS_PENCERESI_MS = 3000;

let sonCikis = 0;

export function cikisiIsaretle(simdi: number = Date.now()): void {
  sonCikis = simdi;
}

/** Bilinçli çıkıştan hemen sonra mıyız (kapı o sırada "sonra" yazmaz). */
export function cikisYeniMi(simdi: number = Date.now()): boolean {
  return simdi - sonCikis < CIKIS_PENCERESI_MS;
}
