/**
 * Karşılama sayfasının ortak parçaları: kapsayıcı, odak halkası, sekme köprüsü.
 *
 * Renkler yalnızca mevcut paletten (docs/design-language.md, globals.css
 * @theme); brief'teki referans renkler rol olarak eşlendi, yeni token yok.
 */

import type { Sekme } from "@/content/landing";

/** 1200px içerik; masaüstünde yanlarda 120px kalır (brief § 1). */
export const KAPSAYICI = "mx-auto w-full max-w-[1200px] px-5 sm:px-8 lg:px-10";

/** Açık zeminde görünür odak halkası. */
export const ODAK =
  "outline-none focus-visible:ring-3 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background";

/** Koyu (ana) zeminde odak halkası: bağlantı rengi orada kaybolur. */
export const ODAK_KOYU =
  "outline-none focus-visible:ring-3 focus-visible:ring-zemin focus-visible:ring-offset-2 focus-visible:ring-offset-ana";

/**
 * Bölüm üst etiketi: cümle düzeninde, büyük harf yok (design-language.md
 * § Kaçınılacaklar). Vurgu rengi zemin üstünde 3:1'de kalıyor; küçük metinde
 * kontrast için ana renk.
 */
export const UST_ETIKET = "text-sm font-semibold text-ana";

/**
 * Menüdeki "Gençler için / Firmalar için" ile "Nasıl çalışır" sekmeleri
 * arasındaki köprü. Menü düzen (layout) tarafında, sekmeler sayfada; ortak
 * durum yerine tarayıcı olayı. Bağlantının kendisi #nasil'e kaydırır.
 */
export const SEKME_OLAYI = "karsilama:sekme";

export function sekmeyiSec(sekme: Sekme) {
  window.dispatchEvent(new CustomEvent<Sekme>(SEKME_OLAYI, { detail: sekme }));
}
