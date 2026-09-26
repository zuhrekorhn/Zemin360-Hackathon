/**
 * Girişe ve role göre yönlendirme kuralları (docs/faz-b-kimlik-ve-dongu.md § 7).
 * Saf fonksiyonlar; testleri yonlendirme.test.ts'de.
 */

import type { Rol } from "@/lib/api";

/** Her rolün paneli: giriş sonrası ve rolü uymayan sayfadan buraya gidilir. */
export function panelYolu(rol: Rol): string {
  if (rol === "genc") return "/genc";
  if (rol === "kurum") return "/kurum";
  return "/girvak";
}

const GIRIS_SAYFALARI = ["/giris", "/kayit"];

/**
 * `?sonra=` güvenli mi? Yalnızca bu sitenin içindeki bir yol kabul edilir:
 * `//baska.site`, `/\baska.site` ya da `https://…` ile açık yönlendirme
 * yapılmasın. Giriş/kayıt sayfasına geri dönmek de anlamsız (döngü).
 */
export function guvenliSonra(sonra: string | null): string | null {
  if (!sonra || !sonra.startsWith("/")) return null;
  if (sonra.startsWith("//") || sonra.startsWith("/\\")) return null;
  const yol = sonra.split(/[?#]/)[0];
  if (GIRIS_SAYFALARI.includes(yol)) return null;
  return sonra;
}

/** Girişten sonra nereye: güvenli bir `sonra` varsa oraya, yoksa panele. */
export function giristenSonra(rol: Rol, sonra: string | null): string {
  return guvenliSonra(sonra) ?? panelYolu(rol);
}
