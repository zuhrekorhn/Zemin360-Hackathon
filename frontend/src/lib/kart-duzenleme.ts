/**
 * Kart düzenleme ekranının karar mantığı (docs/plans/genc-akisi.md § 6).
 * Saf fonksiyonlar; testleri kart-duzenleme.test.ts'de.
 */

import type { ReferansDurumu, SomutCiktiTaslagi } from "@/lib/api";

/** "Python, FastAPI ,, Docker" → ["Python", "FastAPI", "Docker"] (tekrarsız, sıra korunur). */
export function virgulluListe(metin: string): string[] {
  const parcalar = metin
    .split(",")
    .map((parca) => parca.trim())
    .filter(Boolean);
  return [...new Set(parcalar)];
}

export function listeMetni(liste: string[] | undefined): string {
  return (liste ?? []).join(", ");
}

/** Düzenleme formundaki alanlardan gerçekten değişenler (backend de aynı kuralı işletir). */
export function degisenIsKalemiAlanlari(
  eski: SomutCiktiTaslagi,
  yeni: SomutCiktiTaslagi,
): Partial<SomutCiktiTaslagi> {
  const alanlar = [
    "baslik",
    "aciklama",
    "olculebilir_sonuc",
    "kendi_rolu",
    "kanit_linki",
    "is_turu",
  ] as const;
  const normal = (deger: string | null | undefined) => deger?.trim() || null;
  const sonuc: Partial<SomutCiktiTaslagi> = {};
  for (const alan of alanlar) {
    if (normal(eski[alan]) !== normal(yeni[alan])) {
      (sonuc as Record<string, string | null>)[alan] = normal(yeni[alan]);
    }
  }
  return sonuc;
}

/** Bu değişiklik güven göstergesini sıfırlar mı? (İş türü yalnızca etiket.) */
export function gostergeSifirlanir(
  degisenler: Partial<SomutCiktiTaslagi>,
): boolean {
  return Object.keys(degisenler).some((alan) => alan !== "is_turu");
}

/**
 * Referans satırında ek not ve "yeniden iste" düğmesi. Backend'in kuralıyla
 * aynı: işin önceki hâline verilmiş yanıt ya da süresi dolmuş istek yeniden
 * istenebilir; güncel yanıt ya da bekleyen istek istenemez.
 */
export function referansSatiri(referans: ReferansDurumu): {
  not: string | null;
  yenidenIstenebilir: boolean;
} {
  if (referans.durum === "yanitlandi" && !referans.guncel) {
    return {
      not: "Bu yanıt çalışmanın önceki hâline verildi; güven göstergesine girmiyor.",
      yenidenIstenebilir: true,
    };
  }
  if (referans.durum === "yanit_yok") {
    return { not: null, yenidenIstenebilir: true };
  }
  return { not: null, yenidenIstenebilir: false };
}
