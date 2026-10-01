/**
 * Kart düzenleme ekranının karar mantığı (docs/plans/genc-akisi.md § 6).
 * Saf fonksiyonlar; testleri kart-duzenleme.test.ts'de.
 */

import type { KartTaslagi, ReferansDurumu, SomutCiktiTaslagi } from "@/lib/api";

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

/** Kartın üst alanları: taslakta boş olabilir, kayıtlı kartta dolu. */
type KartAlanKaynagi = Pick<
  KartTaslagi,
  | "rol_alani"
  | "deneyim_seviyesi"
  | "sektor_ilgi_alani"
  | "araclar_teknolojiler"
  | "sertifikalar"
  | "diller"
>;

/** Formun tuttuğu hâl: liste alanları virgüllü metin olarak düzenlenir. */
export type KartAlanDegerleri = {
  rol: string;
  deneyim: string;
  sektor: string;
  araclar: string;
  sertifikalar: string;
  diller: string;
};

export function kartAlanDegerleri(kart: KartAlanKaynagi): KartAlanDegerleri {
  return {
    rol: kart.rol_alani ?? "",
    deneyim: kart.deneyim_seviyesi ?? "",
    sektor: listeMetni(kart.sektor_ilgi_alani),
    araclar: listeMetni(kart.araclar_teknolojiler),
    sertifikalar: listeMetni(kart.sertifikalar),
    diller: listeMetni(kart.diller),
  };
}

/** Formdan API'nin beklediği alanlara (kart düzenleme ve Keşif onayı aynı). */
export function kartAlanlariniCevir(degerler: KartAlanDegerleri) {
  return {
    rol_alani: degerler.rol.trim(),
    deneyim_seviyesi: degerler.deneyim,
    sektor_ilgi_alani: virgulluListe(degerler.sektor),
    araclar_teknolojiler: virgulluListe(degerler.araclar),
    sertifikalar: virgulluListe(degerler.sertifikalar),
    diller: virgulluListe(degerler.diller),
  };
}

/**
 * Onay için doldurulması gereken alanlar (backend'deki OnayliKart ile aynı):
 * rol, deneyim ve en az bir sektör. Sohbet netleştiremediyse boş gelir.
 */
export function eksikKartAlanlari(
  degerler: KartAlanDegerleri,
): ("rol" | "deneyim" | "sektor")[] {
  const eksikler: ("rol" | "deneyim" | "sektor")[] = [];
  if (!degerler.rol.trim()) eksikler.push("rol");
  if (!degerler.deneyim) eksikler.push("deneyim");
  if (virgulluListe(degerler.sektor).length === 0) eksikler.push("sektor");
  return eksikler;
}

/**
 * Düzenleme formundaki alanlardan gerçekten değişenler (backend de aynı kuralı
 * işletir). Yalnızca iddianın alanları: kanıt kanıt bölümünden eklenir ve
 * kaldırılır (tek kapı).
 */
export function degisenIsKalemiAlanlari(
  eski: SomutCiktiTaslagi,
  yeni: SomutCiktiTaslagi,
): Partial<Omit<SomutCiktiTaslagi, "kanit_linki">> {
  const alanlar = [
    "baslik",
    "aciklama",
    "olculebilir_sonuc",
    "kendi_rolu",
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
 * Referans satırında ek not ve "yeniden iste" düğmesi. Düğmenin kuralı
 * backend'de tek yerde (`yeniden_istenebilir`); burada tekrar edilmez.
 */
export function referansSatiri(referans: ReferansDurumu): {
  not: string | null;
  yenidenIstenebilir: boolean;
} {
  const eskiHaline =
    referans.durum === "yanitlandi" && !referans.guncel
      ? "Bu yanıt çalışmanın önceki hâline verildi; güven göstergesine girmiyor."
      : null;
  return { not: eskiHaline, yenidenIstenebilir: referans.yeniden_istenebilir };
}
