/**
 * Kart sayfasında çalışmaların eksikleri ve "sıradaki adım" (docs/dogrulama.md § 1).
 * Saf; testi calisma.test.ts'de.
 *
 * Güven göstergesi neyin eksik olduğunu söylüyor ama ne yapılacağını
 * söylemiyordu. Burada her çalışmanın eksik başlıkları sırayla çıkarılır ve
 * kartın tamamı için tek bir adım seçilir: en az eksiği kalan çalışmanın ilk
 * eksiği (en hızlı kazanç). Kartın durumu tek bir puana indirilmez
 * (docs/agent-specs.md § 4); yalnızca eksik başlıklar sayılır.
 *
 * Sıra: kanıt (yoksa ya da çalışmayı göstermiyorsa diğer başlıklar da ona
 * dayanır), sonuç, pay, referans.
 */

import type { GuvenSkoru } from "@/lib/api";

export type AdimTuru = "kanit" | "sonuc" | "rol" | "referans";

export type Eksik = {
  tur: AdimTuru;
  /** Göstergedeki başlık adı. */
  baslik: "Kanıt" | "Sonuç" | "Rol" | "Referans";
  /** Kısa eylem: "Çalışmanın sonucunu yaz". */
  kisa: string;
  /** Bir cümlelik açıklama. */
  metin: string;
  /** Düğme: "Sonucu ekle". */
  etiket: string;
};

/** 0 ve 1 zayıf sayılır; 2 ve üstü yeterli. "—" (null) bu kararda zayıf değil. */
const zayif = (deger: number | null | undefined) =>
  deger !== null && deger !== undefined && deger <= 1;

const KANIT_YOK: Eksik = {
  tur: "kanit",
  baslik: "Kanıt",
  kisa: "Kanıt ekle",
  metin: "Bu çalışmayı gösteren bir link ya da dosya ekle.",
  etiket: "Kanıt ekle",
};
const KANIT_ZAYIF: Eksik = {
  tur: "kanit",
  baslik: "Kanıt",
  kisa: "Doğru kanıtı ekle",
  metin:
    "Eklediğin kanıt bu çalışmanın sana ait olduğunu göstermiyor. Çalışmanın kendi linkini ya da bir dosya ekle.",
  etiket: "Doğru kanıtı ekle",
};
const SONUC: Eksik = {
  tur: "sonuc",
  baslik: "Sonuç",
  kisa: "Çalışmanın sonucunu yaz",
  metin: "Bu çalışma ne sağladı? Sayıyla anlatabilirsen daha güçlü olur.",
  etiket: "Sonucu ekle",
};
const ROL: Eksik = {
  tur: "rol",
  baslik: "Rol",
  kisa: "Payını yaz",
  metin: "Bu çalışmada senin ne yaptığını yaz.",
  etiket: "Payını yaz",
};
const REFERANS: Eksik = {
  tur: "referans",
  baslik: "Referans",
  kisa: "Referans iste",
  metin: "Çalışmanı doğrulayabilecek birinden referans iste.",
  etiket: "Referans iste",
};

export type CalismaDurumu = {
  kanitSayisi: number;
  referansSayisi: number;
  skor: GuvenSkoru | null | undefined;
};

/** Çalışmanın eksik başlıkları, yapılacak sırayla. */
export function eksikler({
  kanitSayisi,
  referansSayisi,
  skor,
}: CalismaDurumu): Eksik[] {
  if (kanitSayisi === 0 && referansSayisi === 0) {
    // Hiçbir şey yokken sonuç ve pay da değerlendirilemez: önce kanıt.
    return [KANIT_YOK];
  }
  // Kanıt var ama henüz değerlendirilmedi: göstergede bir şey yok, öneri de yok.
  if (!skor) return [];
  const liste: Eksik[] = [];
  if (kanitSayisi === 0 && skor.kanit_orijinalligi === null)
    liste.push(KANIT_YOK);
  else if (zayif(skor.kanit_orijinalligi)) liste.push(KANIT_ZAYIF);
  if (zayif(skor.sonuc_olculebilirligi)) liste.push(SONUC);
  if (zayif(skor.rol_netligi)) liste.push(ROL);
  if (
    (skor.ucuncu_taraf_onayi === null && referansSayisi === 0) ||
    zayif(skor.ucuncu_taraf_onayi)
  )
    liste.push(REFERANS);
  return liste;
}

/** Çalışmanın ilk eksiği; eksik yoksa null. */
export function siradakiAdim(durum: CalismaDurumu): Eksik | null {
  return eksikler(durum)[0] ?? null;
}

export type KartAdimi = {
  ciktiId: string;
  calisma: string;
  adim: Eksik;
  eksikSayisi: number;
};

/**
 * Kartın tamamı için tek adım: en az eksiği kalan çalışmanın ilk eksiği.
 * Eşitlikte listedeki sıra. Hiç eksik yoksa null.
 */
export function kartinSiradakiAdimi(
  calismalar: { id: string; baslik: string; eksikler: Eksik[] }[],
): KartAdimi | null {
  let secilen: KartAdimi | null = null;
  for (const calisma of calismalar) {
    const sayi = calisma.eksikler.length;
    if (sayi === 0) continue;
    if (!secilen || sayi < secilen.eksikSayisi) {
      secilen = {
        ciktiId: calisma.id,
        calisma: calisma.baslik,
        adim: calisma.eksikler[0],
        eksikSayisi: sayi,
      };
    }
  }
  return secilen;
}

/** Bandın alt cümlesi: kaç eksik kaldığı. */
export function kalanCumlesi(adim: KartAdimi): string {
  if (adim.eksikSayisi === 1) {
    return `Bu çalışmada yalnızca ${adim.adim.baslik.toLocaleLowerCase("tr")} eksik. Tamamlarsan çalışma güçlü görünür.`;
  }
  return `Bu çalışmada ${adim.eksikSayisi} başlık eksik; en hızlısından başla.`;
}

/** Kartın durumu: çalışma sayısı, eksiksiz çalışma ve eksik başlık toplamı (puan değil). */
export function kartDurumu(eksikListeleri: Eksik[][]): {
  calisma: number;
  tamam: number;
  eksik: number;
} {
  return {
    calisma: eksikListeleri.length,
    tamam: eksikListeleri.filter((l) => l.length === 0).length,
    eksik: eksikListeleri.reduce((t, l) => t + l.length, 0),
  };
}

/**
 * Değerlendirme kart onayından ya da kanıttan sonra arka planda çalışıyor;
 * sayfa açıldığında göstergesi henüz yazılmamış çalışma "bekliyor" görünür.
 * Böyle bir çalışma varsa sayfa kendini yeniler (kart sayfası).
 */
export function degerlendirmeBekliyor(
  ciktilar: readonly { guven_skoru: GuvenSkoru | null }[],
): boolean {
  return ciktilar.some((cikti) => cikti.guven_skoru === null);
}

/** Bekleyen değerlendirme için yenileme aralığı ve en fazla deneme (≈ 1 dk). */
export const YENILEME_ARALIGI_MS = 4000;
export const YENILEME_EN_FAZLA = 15;
