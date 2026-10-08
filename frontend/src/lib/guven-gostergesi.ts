/**
 * Güven göstergesinin bir başlığının gösterimi (docs/dogrulama.md § 1, İ4).
 *
 * Değer kelimeyle ve çubukla gösterilir, "2/3" gibi not biçiminde değil: kelime
 * renge dayanmadan okunur, çubuk bir bakışta karşılaştırılır (karşılama
 * sayfasındaki örnekle aynı dil, docs/icerik-rehberi.md § 4).
 *
 * null = "—": başlık değerlendirilmedi ya da (Referans'ta) yanıt yok. 0 ile
 * karıştırılmaz: 0 bir değerlendirmenin sonucudur ("Eksik"), "—" ise
 * değerlendirme yok demektir. Ekran okuyucu "—"yu okuyamadığı için her değerin
 * bir de sözlü karşılığı var.
 */

import type { GuvenSkoru } from "@/lib/api";

export type BaslikAdi = "Kanıt" | "Sonuç" | "Rol" | "Referans";

/** 0–3 değerinin kelimesi. Karşılama sayfasındaki seviye örneği 1–3'ü kullanır. */
export const SEVIYE_KELIMELERI: Record<number, string> = {
  0: "Eksik",
  1: "Zayıf",
  2: "Orta",
  3: "Güçlü",
};

export type BaslikGosterimi = {
  /** Ekranda görünen: "Orta" ya da "—". */
  metin: string;
  /** Ekran okuyucunun okuduğu. */
  sozlu: string;
  /** Çubuğun dolu parça sayısı (0–3); değerlendirilmemişse null. */
  seviye: number | null;
};

export function baslikGosterimi(
  ad: BaslikAdi,
  deger: number | null,
): BaslikGosterimi {
  if (deger === null) {
    return {
      metin: "—",
      sozlu: ad === "Referans" ? "referans yok" : "değerlendirilmedi",
      seviye: null,
    };
  }
  const kelime = SEVIYE_KELIMELERI[deger] ?? String(deger);
  return {
    metin: kelime,
    sozlu: `${kelime}, 3 üzerinden ${deger}`,
    seviye: deger,
  };
}

/** Göstergenin dört başlığı ve veri alanları (docs/agent-specs.md § 4). */
export const GOSTERGE_BASLIKLARI = [
  { ad: "Kanıt", alan: "kanit_orijinalligi" },
  { ad: "Sonuç", alan: "sonuc_olculebilirligi" },
  { ad: "Rol", alan: "rol_netligi" },
  { ad: "Referans", alan: "ucuncu_taraf_onayi" },
] as const satisfies readonly { ad: BaslikAdi; alan: keyof GuvenSkoru }[];

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

/**
 * Değerlendirme notunu başlıklarına ayırır. Not "Kanıt: … Sonuç: … Rol: …" diye
 * tek paragraf geliyor (app/agents/dogrulama); her başlığın notu kendi
 * göstergesinin yanında okunsun diye bölünür. Başlıksız not tek parça döner.
 */
export function notuBasliklaraAyir(
  not: string | null | undefined,
): { baslik: BaslikAdi | null; metin: string }[] {
  if (!not?.trim()) return [];
  const kalip = /(Kanıt|Sonuç|Rol|Referans):\s*/g;
  const eslesmeler = [...not.matchAll(kalip)];
  if (eslesmeler.length === 0) return [{ baslik: null, metin: not.trim() }];
  const parcalar: { baslik: BaslikAdi | null; metin: string }[] = [];
  const once = not.slice(0, eslesmeler[0].index).trim();
  if (once) parcalar.push({ baslik: null, metin: once });
  eslesmeler.forEach((eslesme, i) => {
    const bas = (eslesme.index ?? 0) + eslesme[0].length;
    const son = eslesmeler[i + 1]?.index ?? not.length;
    const metin = not.slice(bas, son).trim();
    if (metin) parcalar.push({ baslik: eslesme[1] as BaslikAdi, metin });
  });
  return parcalar;
}

/**
 * Notun ilk cümlesi. Değerlendirme notunun son başlığı genel bir öneriyle
 * bitiyor ("… açıkça belirtebilirsin"); adımın yanında yalnızca o başlığın
 * kendi tespiti gösterilir.
 */
export function ilkCumle(metin: string): string {
  const eslesme = metin.match(/^.*?[.!?](?=\s|$)/);
  return (eslesme ? eslesme[0] : metin).trim();
}
