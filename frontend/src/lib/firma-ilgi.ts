/**
 * Aday firmanın ilgi akışı (docs/kararlar.md F8).
 * Saf fonksiyonlar; testleri firma-ilgi.test.ts'de. Firmaya "siz".
 *
 * Durum makinesi gençtekiyle aynı: aday firma "aday tarafı"dır. `baslatan`
 * ilk ilgiyi kimin gösterdiği ("genc" = aday tarafı, "kurum" = ilanı açan).
 */

import type { FirmaAdayEslesmesi } from "@/lib/api";

/** Aday firmanın gördüğü etiketler: rehber § 5.9 "Genç görür" sütununun "siz" hâli. */
const ADAY_FIRMA_ETIKETLERI: Record<string, string> = {
  onerildi: "Size uygun",
  genc_ilgilendi: "İlginiz iletildi",
  ilgileniliyor: "Firma sizinle ilgileniyor",
  kabul_edildi: "Karşılıklı ilgi",
  reddedildi: "Kapandı",
  kapandi: "Kapandı",
};

export function adayFirmaDurumEtiketi(durum: string): string {
  return ADAY_FIRMA_ETIKETLERI[durum] ?? "Durumu güncelleniyor";
}

/** Açık onay: ilanı açan firma da ilgilenirse e-posta ayrıca sorulmadan paylaşılır. */
export const FIRMA_ILETISIM_ONAYI =
  "İhtiyacın sahibi firma da ilgilenirse e-posta adresiniz, size ayrıca sorulmadan o firmayla paylaşılır.";

/** Firmanın aday olduğu eşleşmeler üç bölüme: fırsatlar, gelen ilgiler, ilgilerimiz. */
export function adayEslesmeleriniAyir(eslesmeler: FirmaAdayEslesmesi[]): {
  firsatlar: FirmaAdayEslesmesi[];
  gelenler: FirmaAdayEslesmesi[];
  ilgilerimiz: FirmaAdayEslesmesi[];
} {
  return {
    firsatlar: eslesmeler.filter((e) => e.durum === "onerildi"),
    // İlk ilgiyi ilanı açan firma gösterdi: kabul / şimdilik değil.
    gelenler: eslesmeler.filter(
      (e) => e.durum !== "onerildi" && e.baslatan === "kurum",
    ),
    // İlk ilgiyi bu firma gösterdi: bekleyiş, karşılıklı ilgi, kapandı.
    ilgilerimiz: eslesmeler.filter(
      (e) => e.durum !== "onerildi" && e.baslatan === "genc",
    ),
  };
}

/** Aday firmanın bir satırda yapabilecekleri (backend de aynı kuralı işletir). */
export function adayFirmaEylemleri(durum: string): {
  ilgiGoster: boolean;
  geriCek: boolean;
  kabulVeyaRed: boolean;
} {
  return {
    ilgiGoster: durum === "onerildi",
    geriCek: durum === "genc_ilgilendi",
    kabulVeyaRed: durum === "ilgileniliyor",
  };
}
