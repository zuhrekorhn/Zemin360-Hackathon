/**
 * Keşif sohbetinin kimliğini tarayıcıda saklar: sayfa yenilenince ya da sekme
 * kapanınca gencin anlattıkları kaybolmasın (GET /kesif/sohbet/{id} ile geri
 * yüklenir). Kimlik bir sır değil: sohbeti yalnızca açan hesap okuyabilir.
 * Depolama kapalı olabilir (özel pencere, engelli site verisi): hata sessizce
 * yutulur, sohbet yine çalışır, yalnızca yenilemede devam etmez.
 */

const ANAHTAR = "zemin360.kesif.oturum";

export function kayitliSohbet(): string | null {
  try {
    return window.localStorage.getItem(ANAHTAR);
  } catch {
    return null;
  }
}

export function sohbetiKaydet(oturumId: string): void {
  try {
    window.localStorage.setItem(ANAHTAR, oturumId);
  } catch {
    // Depolama yok: yenilemede devam edilemez, başka bir şey bozulmaz.
  }
}

export function sohbetiUnut(): void {
  try {
    window.localStorage.removeItem(ANAHTAR);
  } catch {
    // Aynı gerekçe.
  }
}
