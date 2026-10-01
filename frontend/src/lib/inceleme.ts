/**
 * GİRVAK inceleme kuyruğunun metinleri (docs/plans/dogrulama-iyilestirme.md § 9).
 * Saf fonksiyonlar; testleri inceleme.test.ts'de. GİRVAK'a "siz".
 */

import type { IncelemeSatiri } from "@/lib/api";

const TUR_ETIKETLERI: Record<string, string> = {
  itiraz_siniri: "İtiraz hakkı doldu",
  ad_degisikligi: "Ad değişikliği talebi",
  ayni_iddia_cok_hesapta: "Aynı çalışma başka bir hesapta",
  ayni_belge_iki_hesapta: "Aynı belge başka bir hesapta",
  gorsel_baskasinda: "Görsel başka bir portfolyoda",
  referans_supheli: "Şüpheli referans yanıtı",
  belge_tutarsiz: "Belge tutarsız",
  kanit_celisiyor: "Kanıt iddiayla çelişiyor",
  profil_kodu_elle: "Profil kodu elle doğrulanacak",
  eposta_barkodu: "e-Devlet barkodu doğrulanacak",
};

export function turEtiketi(tur: string): string {
  return TUR_ETIKETLERI[tur] ?? "İnceleme";
}

/** Karar düğmeleri: talepte onay/ret, sinyalde "sorun yok" / "doğrulanamadı". */
export function kararEtiketleri(tur: string): {
  kapandi: string;
  dogrulanamadi: string;
} {
  return tur === "ad_degisikligi"
    ? { kapandi: "Onayla", dogrulanamadi: "Reddet" }
    : { kapandi: "Sorun yok", dogrulanamadi: "Doğrulanamadı" };
}

function metinListesi(deger: unknown): string[] {
  return Array.isArray(deger)
    ? deger.filter((d): d is string => typeof d === "string")
    : [];
}

/** Ayrıntının GİRVAK'a gösterilen satırları (türe göre). */
export function ayrintiSatirlari(satir: IncelemeSatiri): string[] {
  const a = satir.ayrinti;
  if (satir.tur === "ad_degisikligi") {
    const satirlar = [`${String(a.eski_ad ?? "—")} → ${String(a.yeni_ad ?? "—")}`];
    if (typeof a.gerekce === "string" && a.gerekce)
      satirlar.push(`Gerekçe: ${a.gerekce}`);
    return satirlar;
  }
  if (satir.tur === "itiraz_siniri") {
    return metinListesi(a.itiraz_notlari).map((n) => `İtiraz notu: ${n}`);
  }
  return [];
}
