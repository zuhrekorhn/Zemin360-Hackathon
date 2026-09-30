/**
 * Hitap (docs/icerik-rehberi.md § 3): gence "sen", firmaya ve GİRVAK'a "siz".
 *
 * İki tarafın birlikte gördüğü ekranlarda (iş birliği sayfası, bildirimler,
 * hata kutusu, sohbet alanı) kimin baktığına göre değişen parçalar bu
 * seçimle yazılır. Giriş yapmamış ziyaretçiye (giriş, kayıt) "sen".
 */

import type { Rol } from "@/lib/api";

export type Hitap = "sen" | "siz";

export function hitapRolden(rol: Rol | null | undefined): Hitap {
  return rol === "kurum" || rol === "girvak" ? "siz" : "sen";
}

/** Aynı cümlenin iki hâli arasından hitaba uyanı. */
export function hitapla(hitap: Hitap, sen: string, siz: string): string {
  return hitap === "siz" ? siz : sen;
}
