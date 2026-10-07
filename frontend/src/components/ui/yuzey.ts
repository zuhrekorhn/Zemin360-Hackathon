/**
 * Kutu yüzeyleri (docs/design-language.md § Yerleşim): zeminden bir ton açık,
 * hairline kenar, çok hafif gölge. Bütün kart ve yan kutular aynı yüzeyi giyer.
 */
export const KUTU =
  "rounded-xl border border-kenar bg-card shadow-[0_1px_2px_rgb(22_33_27/0.05)]";

/** Zayıf ya da eksik bir şeye dikkat çeken yüzey (amber, kesikli). */
export const DIKKAT = "border border-dashed border-vurgu/60 bg-vurgu/[0.08]";
