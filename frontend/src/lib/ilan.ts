/**
 * İlan (ihtiyaç kartı) kapatma (docs/plans/firma-akisi.md § 0 karar 7, § 7).
 * Saf fonksiyonlar; testleri ilan.test.ts'de. Firmaya "siz".
 *
 * Neden yalnızca GİRVAK'a görünür; karşı taraf "fırsat kapandı" görür.
 * Kapanan ilan tekrar açılmaz.
 */

import type { IhtiyacKartiOzeti } from "@/lib/api";

export type KapanmaNedeni =
  "platformda_bulundu" | "baska_yoldan_bulundu" | "vazgecildi";

export const KAPANMA_NEDENLERI: { deger: KapanmaNedeni; etiket: string }[] = [
  { deger: "platformda_bulundu", etiket: "Platformda bulduk" },
  { deger: "baska_yoldan_bulundu", etiket: "Başka yoldan bulduk" },
  { deger: "vazgecildi", etiket: "Vazgeçtik" },
];

export function ilanKapali(ilan: Pick<IhtiyacKartiOzeti, "durum">): boolean {
  return ilan.durum === "kapandi";
}

/** Açık ilanlar önce, kapalılar sona; her grup kendi içinde gelen sırayı korur. */
export function ilanlariSirala<T extends Pick<IhtiyacKartiOzeti, "durum">>(
  ilanlar: T[],
): T[] {
  return [
    ...ilanlar.filter((ilan) => !ilanKapali(ilan)),
    ...ilanlar.filter(ilanKapali),
  ];
}
