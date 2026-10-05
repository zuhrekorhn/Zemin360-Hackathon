/**
 * Açık sohbetin kimliği sekme ömrü boyunca hatırlanır (sessionStorage).
 *
 * Sohbetin kendisi backend'de (checkpointer) duruyor; sayfa yenilenince
 * kaybolan yalnızca kimlikti. Depolama kapalıysa (gizli pencere, engelli site
 * verisi) okuma/yazma sessizce başarısız olur ve yeni sohbet açılır.
 */

export function sohbetOturumuOku(anahtar: string): string | null {
  try {
    return window.sessionStorage.getItem(anahtar);
  } catch {
    return null;
  }
}

export function sohbetOturumuYaz(anahtar: string, oturumId: string): void {
  try {
    window.sessionStorage.setItem(anahtar, oturumId);
  } catch {
    // Depolama yoksa yenilemede yeni sohbet açılır; akış bozulmaz.
  }
}

export function sohbetOturumuSil(anahtar: string): void {
  try {
    window.sessionStorage.removeItem(anahtar);
  } catch {
    // Bkz. sohbetOturumuYaz.
  }
}
