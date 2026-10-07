/**
 * Güven göstergesinin bir başlığının gösterimi (docs/dogrulama.md § 1, İ4).
 *
 * null = "—": başlık değerlendirilmedi ya da (Referans'ta) yanıt yok. 0 ile
 * karıştırılmaz: 0 bir değerlendirmenin sonucudur (ör. referans olumsuz yanıt
 * verdi), "—" ise değerlendirme yok demektir. Ekran okuyucu "—"yu okuyamadığı
 * için her değerin bir de sözlü karşılığı var.
 */

import type { GuvenSkoru } from "@/lib/api";

export type BaslikAdi = "Kanıt" | "Sonuç" | "Rol" | "Referans";

export type BaslikGosterimi = {
  /** Ekranda görünen: "2/3" ya da "—". */
  metin: string;
  /** Ekran okuyucunun okuduğu. */
  sozlu: string;
};

export function baslikGosterimi(
  ad: BaslikAdi,
  deger: number | null,
): BaslikGosterimi {
  if (deger === null) {
    return {
      metin: "—",
      sozlu: ad === "Referans" ? "referans yok" : "değerlendirilmedi",
    };
  }
  return { metin: `${deger}/3`, sozlu: `3 üzerinden ${deger}` };
}

/**
 * Göstergede gösterilecek bir şey var mı? Dört başlık da "—" ise (ör. çalışmanın
 * tek kanıtı kaldırıldı ve referans yanıtı yok) gösterge yokmuş gibi davranılır:
 * dört tire yerine "henüz değerlendirilmedi" denir.
 */
export function gostergeDoluMu(skor: GuvenSkoru | null | undefined): boolean {
  if (!skor) return false;
  return [
    skor.kanit_orijinalligi,
    skor.sonuc_olculebilirligi,
    skor.rol_netligi,
    skor.ucuncu_taraf_onayi,
  ].some((deger) => deger !== null);
}
