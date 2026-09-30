/**
 * İlan (ihtiyaç kartı) kapatma (docs/plans/firma-akisi.md § 0 karar 7, § 7).
 * Saf fonksiyonlar; testleri ilan.test.ts'de. Firmaya "siz".
 *
 * Neden yalnızca GİRVAK'a görünür; karşı taraf "fırsat kapandı" görür.
 * Kapanan ilan tekrar açılmaz.
 */

import type { IhtiyacKartiOzeti } from "@/lib/api";

export type KapanmaNedeni =
  "platformda_bulundu" | "baska_yoldan_bulundu" | "vazgecildi";

export const KAPANMA_NEDENLERI: { deger: KapanmaNedeni; etiket: string }[] = [
  { deger: "platformda_bulundu", etiket: "Platformda bulduk" },
  { deger: "baska_yoldan_bulundu", etiket: "Başka yoldan bulduk" },
  { deger: "vazgecildi", etiket: "Vazgeçtik" },
];

export function ilanKapali(ilan: Pick<IhtiyacKartiOzeti, "durum">): boolean {
  return ilan.durum === "kapandi";
}

/** Açık ilanlar önce, kapalılar sona; her grup kendi içinde gelen sırayı korur. */
export function ilanlariSirala<T extends Pick<IhtiyacKartiOzeti, "durum">>(
  ilanlar: T[],
): T[] {
  return [
    ...ilanlar.filter((ilan) => !ilanKapali(ilan)),
    ...ilanlar.filter(ilanKapali),
  ];
}

/* --- İki kapı (docs/plans/firma-akisi.md § 0 kararlar 4-5) --------------- */

export type Aranan = "genc" | "firma";

/** `/tanimlama?aranan=` değeri; tanınmayan ya da boş değer genç kapısı. */
export function arananParametresi(deger: string | null): Aranan {
  return deger === "firma" ? "firma" : "genc";
}

export const KAPILAR: {
  aranan: Aranan;
  baslik: string;
  aciklama: string;
  yol: string;
}[] = [
  {
    aranan: "genc",
    baslik: "Genç yetenek bul",
    aciklama: "Bir ihtiyacınızı tanımlayın, ona uygun genç yetenekleri görün.",
    yol: "/tanimlama",
  },
  {
    aranan: "firma",
    baslik: "İş birliği ortağı bul",
    aciklama:
      "Bir iş için ortak arayın: girişim, KOBİ ya da kurumsal firmalar önerilsin.",
    yol: "/tanimlama?aranan=firma",
  },
];

/** Panelde ortak ilanının yanındaki etiket; genç ilanında etiket yok. */
export function arananEtiketi(aranan: Aranan): string | null {
  return aranan === "firma" ? "İş birliği ortağı" : null;
}
