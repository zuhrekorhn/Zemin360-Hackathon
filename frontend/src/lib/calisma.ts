/**
 * Kart sayfasında bir çalışmanın "sıradaki adımı" (docs/dogrulama.md § 1).
 * Saf; testi calisma.test.ts'de.
 *
 * Güven göstergesi neyin eksik olduğunu söylüyor ama ne yapılacağını
 * söylemiyordu; genç dört başlığı ve uzun notu okuyup kendisi çıkarıyordu.
 * Burada en zayıf başlıktan tek bir eylem seçilir. Sıra, gencin en az
 * emekle en çok fark yaratacağı yerden: kanıt hiç yoksa kanıt; sonra kendi
 * yazacağı iki şey (sonuç, pay); sonra daha güçlü kanıt; en son referans
 * (başkasının yanıtına bağlı).
 */

import type { GuvenSkoru } from "@/lib/api";

export type AdimTuru = "kanit" | "sonuc" | "rol" | "referans";

export type SiradakiAdim = {
  tur: AdimTuru;
  metin: string;
  etiket: string;
};

/** 0 ve 1 zayıf sayılır; 2 ve üstü yeterli. "—" (null) bu kararda zayıf değil. */
const zayif = (deger: number | null | undefined) =>
  deger !== null && deger !== undefined && deger <= 1;

export function siradakiAdim({
  kanitSayisi,
  referansSayisi,
  skor,
}: {
  kanitSayisi: number;
  referansSayisi: number;
  skor: GuvenSkoru | null | undefined;
}): SiradakiAdim | null {
  if (kanitSayisi === 0 && referansSayisi === 0) {
    return {
      tur: "kanit",
      metin: "Bu çalışmayı gösteren bir link ya da dosya ekle.",
      etiket: "Kanıt ekle",
    };
  }
  // Kanıt var ama henüz değerlendirilmedi: kanıt bölümü kendi düğmesini gösterir.
  if (!skor) return null;
  if (zayif(skor.sonuc_olculebilirligi)) {
    return {
      tur: "sonuc",
      metin:
        "Çalışmanın getirdiği sonucu yaz; sayıyla anlatabilirsen daha güçlü olur.",
      etiket: "Sonucu ekle",
    };
  }
  if (zayif(skor.rol_netligi)) {
    return {
      tur: "rol",
      metin: "Bu çalışmada senin ne yaptığını yaz.",
      etiket: "Payını yaz",
    };
  }
  if (zayif(skor.kanit_orijinalligi)) {
    return {
      tur: "kanit",
      metin:
        "Çalışmanın sana ait olduğunu gösteren bir kanıt ekle; hesabını bağlamak da işe yarar.",
      etiket: "Kanıt ekle",
    };
  }
  if (skor.ucuncu_taraf_onayi === null && referansSayisi === 0) {
    return {
      tur: "referans",
      metin: "Çalışmanı doğrulayabilecek birinden referans iste.",
      etiket: "Referans iste",
    };
  }
  return null;
}
