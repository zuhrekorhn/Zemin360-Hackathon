"use client";

import { useEffect } from "react";

/** Sekme başlığının eki; kök düzendeki başlıkla aynı ad. */
const MARKA = "Zemin360";

/** "Panelim · Zemin360" biçimi. Boşsa yalnızca marka. Saf; testi sekme-basligi.test.ts'de. */
export function sekmeBasligi(sayfa: string | null | undefined): string {
  const ad = sayfa?.trim();
  return ad ? `${ad} · ${MARKA}` : MARKA;
}

/**
 * Sayfanın sekme başlığını ayarlar. Sayfalar istemci bileşeni olduğu için
 * `metadata` dışa aktaramaz; her sayfa `SayfaBasligi` ile bunu kendiliğinden
 * yapar, özel başlıklı sayfalar (Panelim, Fırsatlar) doğrudan çağırır.
 * Birden çok sekme açıkken ve ekran paylaşırken sayfalar ayırt edilsin diye.
 */
export function useSekmeBasligi(sayfa: string | null | undefined): void {
  useEffect(() => {
    if (!sayfa) return;
    document.title = sekmeBasligi(sayfa);
  }, [sayfa]);
}
