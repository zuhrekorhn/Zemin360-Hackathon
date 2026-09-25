/**
 * Oturum token'ı (docs/faz-b-kimlik-ve-dongu.md § 1).
 *
 * JWT localStorage'da tutulur ve her istekte `Authorization: Bearer` ile
 * gider (lib/api.ts). Çıkış = token'ı silmek; sunucuda iptal listesi yok.
 * httpOnly cookie'ye geçiş ürünleşme dönemine bırakıldı (roadmap § Kapsam dışı).
 *
 * localStorage gizli sekmede ya da kapalı depolamada hata fırlatabilir; o
 * durumda token yokmuş gibi davranılır (kullanıcı girişe yönlenir).
 */

const ANAHTAR = "zemin360.token";

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
}

export function tokenSil(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(ANAHTAR);
  } catch {
    // Silinemiyorsa zaten okunamıyordur.
  }
}
