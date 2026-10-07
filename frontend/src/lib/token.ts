/**
 * Oturum token'ı (docs/kimlik-ve-dongu.md § 1).
 *
 * JWT localStorage'da tutulur ve her istekte `Authorization: Bearer` ile
 * gider (lib/api.ts). Çıkış = token'ı silmek; sunucuda iptal listesi yok.
 * httpOnly cookie'ye geçiş ürünleşme dönemine bırakıldı (roadmap § Kapsam dışı).
 *
 * localStorage gizli sekmede ya da kapalı depolamada hata fırlatabilir; o
 * durumda token yokmuş gibi davranılır (kullanıcı girişe yönlenir).
 *
 * Token değişince `TOKEN_DEGISTI` olayı yayılır: 401 yüzünden silinen token
 * da dahil. Oturum sağlayıcısı (lib/oturum.tsx) bunu dinleyip menüyü ve
 * yönlendirmeyi hemen günceller; başka sekmedeki değişiklik `storage`
 * olayıyla gelir.
 */

const ANAHTAR = "zemin360.token";
export const TOKEN_DEGISTI = "zemin360:token-degisti";

function haberVer(): void {
  window.dispatchEvent(new Event(TOKEN_DEGISTI));
}

export function tokenOku(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(ANAHTAR);
  } catch {
    return null;
  }
}

export function tokenYaz(token: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(ANAHTAR, token);
  } catch {
    // Yazılamadıysa oturum bu sekmede kalıcı olmaz; akış bozulmaz.
  }
  haberVer();
}

export function tokenSil(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(ANAHTAR);
  } catch {
    // Silinemiyorsa zaten okunamıyordur.
  }
  haberVer();
}

/** Başka sekmede giriş/çıkış yapıldıysa `storage` olayı bu anahtar için gelir. */
export function tokenAnahtariMi(anahtar: string | null): boolean {
  return anahtar === ANAHTAR;
}
