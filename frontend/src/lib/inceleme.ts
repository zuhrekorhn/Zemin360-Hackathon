/**
 * GİRVAK inceleme kuyruğunun metinleri (docs/dogrulama.md § 9).
 * Saf fonksiyonlar; testleri inceleme.test.ts'de. GİRVAK'a "siz".
 */

import type { IncelemeSatiri } from "@/lib/api";
import { platformAdi } from "@/lib/hesap-baglama";

const TUR_ETIKETLERI: Record<string, string> = {
  itiraz_siniri: "Gencin itiraz hakkı doldu",
  ad_degisikligi: "Ad değişikliği talebi",
  ayni_iddia_cok_hesapta: "Aynı çalışma başka bir hesapta",
  ayni_belge_iki_hesapta: "Aynı belge başka bir hesapta",
  gorsel_baskasinda: "Görsel başka bir sayfada da var",
  referans_supheli: "Şüpheli referans yanıtı",
  belge_tutarsiz: "Belgede tutarsızlık var",
  kanit_celisiyor: "Kanıt, çalışmanın anlatımıyla çelişiyor",
  profil_kodu_elle: "Doğrulama kodunu elle kontrol edin",
  edevlet_barkodu: "e-Devlet belgesini doğrulayın",
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
    return {
      kapandi: "Kod profilde var, hesabı bağla",
      dogrulanamadi: "Kod yok",
    };
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

// Dosyası incelenecek işaretler: ayrıntıdaki listenin adı (e-Devlet barkodu,
// bozuk imza / adsız doğrulama sayfası, başka sayfada bulunan görsel).
const BELGE_LISTELERI: Record<string, string> = {
  edevlet_barkodu: "parcalar",
  belge_tutarsiz: "bulgular",
  gorsel_baskasinda: "sayfalar",
};

/** İşaretin indirilecek belgeleri: GİRVAK dosyayı açıp kendisi bakar. */
export function incelenecekBelgeler(satir: IncelemeSatiri): string[] {
  const liste = BELGE_LISTELERI[satir.tur];
  if (!liste) return [];
  const idler = nesneListesi(satir.ayrinti[liste])
    .map((p) => p.parca_id)
    .filter((id): id is string => typeof id === "string");
  return [...new Set(idler)];
}

const IDDIA_ADLARI: Record<string, string> = {
  is: "Çalışma",
  sonuc: "Sonuç",
  pay: "Rol",
};

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

/** Referans yanıtının şüphe sinyalleri (backend: agents/dogrulama/referans_suphesi.py). */
function referansSinyali(sinyal: string, r: Record<string, unknown>): string {
  switch (sinyal) {
    case "ip_genc_ile_ayni":
      return "gençle aynı internet bağlantısından yanıtlanmış";
    case "tarayici_genc_ile_ayni":
      return "gencin kendi tarayıcısından yanıtlanmış";
    case "hizli_yanit":
      return `form yalnızca ${String(r.form_suresi_sn ?? "birkaç")} saniyede doldurulmuş`;
    case "form_acilmadan":
      return "form sayfası hiç açılmadan yanıt gelmiş";
    case "cok_gence_yanit":
      return `bu kişi ${String(r.genc_sayisi ?? "birçok")} farklı gence referans vermiş`;
    default:
      return sinyal;
  }
}

/**
 * Ayrıntının GİRVAK'a gösterilen satırları: türe özel satırlar, ardından gencin
 * itiraz notları ("doğrulanamadı" kararına itiraz aynı türden yeni işaret açar).
 */
export function ayrintiSatirlari(satir: IncelemeSatiri): string[] {
  const notlar = metinListesi(satir.ayrinti.itiraz_notlari).map(
    (n) => `İtiraz notu: ${n}`,
  );
  if (satir.tur === "itiraz_siniri") return notlar;
  const itiraz = notlar.length
    ? ["Genç önceki “doğrulanamadı” kararına itiraz etti.", ...notlar]
    : [];
  return [...turSatirlari(satir), ...itiraz];
}

function turSatirlari(satir: IncelemeSatiri): string[] {
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
  if (satir.tur === "referans_supheli") {
    return nesneListesi(a.referanslar).map(
      (r) =>
        `Neden şüpheli: ${metinListesi(r.sinyaller)
          .map((sinyal) => referansSinyali(sinyal, r))
          .join(" · ")}`,
    );
  }
  if (satir.tur === "belge_tutarsiz") {
    return nesneListesi(a.bulgular).map((b) =>
      b.neden === "bozuk_imza"
        ? `E-imza geçersiz ya da belge imzadan sonra değişmiş: ${String(b.dosya_adi ?? "—")}`
        : `Doğrulama sayfasında gencin adı ya da e-postası geçmiyor: ${String(b.adres ?? "—")}`,
    );
  }
  if (satir.tur === "kanit_celisiyor") {
    return nesneListesi(a.celiskiler).map(
      (c) =>
        `${IDDIA_ADLARI[String(c.iddia)] ?? "İddia"} kanıtla çelişiyor: “${String(c.alinti ?? "—")}” (${String(c.adres ?? c.dosya_adi ?? "—")})`,
    );
  }
  if (satir.tur === "gorsel_baskasinda") {
    return nesneListesi(a.sayfalar).map(
      (g) =>
        `${String(g.dosya_adi ?? "Görsel")} şu sayfada da var: ${String(g.adres ?? "—")}`,
    );
  }
  return [];
}
