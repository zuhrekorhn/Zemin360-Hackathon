/**
 * Giriş/kayıt akışı Faz 3'te geleceği için kimlikler tarayıcıda tutuluyor:
 * Keşif'te oluşan yetenek kartı ve Tanımlama'da oluşan kurum kimliği.
 * Bilinçli MVP kısıtı — oturum değil, yalnızca "en son şunu oluşturmuştun"
 * hatırlatması. Sunucuda hiçbir şeye yetki vermiyor.
 */

const ANAHTARLAR = {
  kart: "zemin360.yetenek_karti_id",
  kurum: "zemin360.kurum_id",
} as const;

type Tur = keyof typeof ANAHTARLAR;

export function kimlikOku(tur: Tur): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(ANAHTARLAR[tur]);
  } catch {
    // Gizli sekme / depolama kapalı — kimlik yokmuş gibi davran.
    return null;
  }
}

export function kimlikYaz(tur: Tur, deger: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(ANAHTARLAR[tur], deger);
  } catch {
    // Yazamadıysak akış bozulmaz, sadece hatırlanmaz.
  }
}
