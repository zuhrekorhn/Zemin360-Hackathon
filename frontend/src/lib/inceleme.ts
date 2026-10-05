/**
 * GİRVAK inceleme kuyruğunun metinleri (docs/plans/dogrulama-iyilestirme.md § 9).
 * Saf fonksiyonlar; testleri inceleme.test.ts'de. GİRVAK'a "siz".
 */

import type { IncelemeSatiri } from "@/lib/api";
import { platformAdi } from "@/lib/hesap-baglama";

const TUR_ETIKETLERI: Record<string, string> = {
  itiraz_siniri: "İtiraz hakkı doldu",
  ad_degisikligi: "Ad değişikliği talebi",
  ayni_iddia_cok_hesapta: "Aynı çalışma başka bir hesapta",
  ayni_belge_iki_hesapta: "Aynı belge başka bir hesapta",
  gorsel_baskasinda: "Görsel başka bir portfolyoda",
  referans_supheli: "Şüpheli referans yanıtı",
  belge_tutarsiz: "Belge tutarsız",
  kanit_celisiyor: "Kanıt iddiayla çelişiyor",
  profil_kodu_elle: "Doğrulama kodu elle kontrol edilecek",
  edevlet_barkodu: "e-Devlet barkodu doğrulanacak",
};

export function turEtiketi(tur: string): string {
  return TUR_ETIKETLERI[tur] ?? "İnceleme";
}

/** Karar düğmeleri: talepte onay/ret, sinyalde "sorun yok" / "doğrulanamadı". */
export function kararEtiketleri(tur: string): {
  kapandi: string;
  dogrulanamadi: string;
} {
  if (tur === "ad_degisikligi")
    return { kapandi: "Onayla", dogrulanamadi: "Reddet" };
  if (tur === "profil_kodu_elle")
    return { kapandi: "Kod profilde, bağla", dogrulanamadi: "Kod yok" };
  if (tur === "edevlet_barkodu")
    return { kapandi: "Belge doğrulandı", dogrulanamadi: "Doğrulanamadı" };
  return { kapandi: "Sorun yok", dogrulanamadi: "Doğrulanamadı" };
}

function metinListesi(deger: unknown): string[] {
  return Array.isArray(deger)
    ? deger.filter((d): d is string => typeof d === "string")
    : [];
}

function nesneListesi(deger: unknown): Record<string, unknown>[] {
  return Array.isArray(deger)
    ? deger.filter(
        (d): d is Record<string, unknown> =>
          typeof d === "object" && d !== null,
      )
    : [];
}

/** İşaretin indirilecek belgeleri (e-Devlet barkodu: GİRVAK belgeyi açıp barkodu okur). */
export function incelenecekBelgeler(satir: IncelemeSatiri): string[] {
  if (satir.tur !== "edevlet_barkodu") return [];
  return nesneListesi(satir.ayrinti.parcalar)
    .map((p) => p.parca_id)
    .filter((id): id is string => typeof id === "string");
}

/** Eşleşmedeki öteki gençlerin kartları (aynı çalışma başka hesapta): GİRVAK karşılaştırır. */
export function karsilastirilacakKartlar(satir: IncelemeSatiri): string[] {
  const kartlar = nesneListesi(satir.ayrinti.eslesmeler)
    .map((e) => e.diger_kart_id)
    .filter((id): id is string => typeof id === "string");
  return [...new Set(kartlar)];
}

const TEKRAR_NEDENLERI: Record<string, string> = {
  adres: "Aynı link başka bir hesapta da var",
  dosya: "Aynı dosya başka bir hesapta da var",
  gorsel: "Benzer görsel başka bir hesapta da var",
};

/** Ayrıntının GİRVAK'a gösterilen satırları (türe göre). */
export function ayrintiSatirlari(satir: IncelemeSatiri): string[] {
  const a = satir.ayrinti;
  if (satir.tur === "ad_degisikligi") {
    const satirlar = [
      `${String(a.eski_ad ?? "—")} → ${String(a.yeni_ad ?? "—")}`,
    ];
    if (typeof a.gerekce === "string" && a.gerekce)
      satirlar.push(`Gerekçe: ${a.gerekce}`);
    return satirlar;
  }
  if (satir.tur === "profil_kodu_elle") {
    // Profil otomatik okunamadı (bot engeli, giriş duvarı): GİRVAK profili açıp
    // açıklamada kodu arar. Ekran görüntüsü kabul edilmez (§ 6.2).
    return [
      `Hesap: ${platformAdi(String(a.platform ?? ""))} · ${String(a.kullanici_adi ?? "—")}`,
      `Profil: ${String(a.profil_adresi ?? "—")}`,
      `Aranacak kod: ${String(a.kod ?? "—")}`,
    ];
  }
  if (satir.tur === "edevlet_barkodu") {
    // Barkod turkiye.gov.tr/belge-dogrulama'da, belgedeki T.C. kimlik no ile
    // sorgulanır; numara saklanmaz, belgenin kendisinden okunur (§ 4.2).
    return nesneListesi(a.parcalar).map(
      (p) =>
        `Barkod: ${String(p.barkod ?? "—")} (turkiye.gov.tr/belge-dogrulama)`,
    );
  }
  if (satir.tur === "ayni_belge_iki_hesapta") {
    return nesneListesi(a.eslesmeler).map(
      (e) =>
        `Doğrulama adresi başka bir hesapta da var: ${String(e.adres ?? "—")}`,
    );
  }
  if (satir.tur === "ayni_iddia_cok_hesapta") {
    return nesneListesi(a.eslesmeler).map(
      (e) =>
        `${TEKRAR_NEDENLERI[String(e.neden)] ?? "Başka bir hesapta da var"}: ${String(e.adres ?? e.dosya_adi ?? "—")}`,
    );
  }
  if (satir.tur === "itiraz_siniri") {
    return metinListesi(a.itiraz_notlari).map((n) => `İtiraz notu: ${n}`);
  }
  return [];
}
