/**
 * Firma–firma eşleşmesinde yapay zekâ kararı (docs/matching-algorithm.md § 8).
 * API yalnızca "uygun", "kismen" ya da null (karar bilinmiyor) döner; "uygun_degil"
 * kayıtlar hiçbir yanıtta yoktur. Rozet yalnızca "kismen" için çizilir.
 */
export type Uygunluk = "uygun" | "kismen" | null;

export const KISMEN_UYGUN_ROZETI = "Kısmen uygun";

export function uygunlukRozeti(uygunluk: Uygunluk | undefined): string | null {
  return uygunluk === "kismen" ? KISMEN_UYGUN_ROZETI : null;
}
