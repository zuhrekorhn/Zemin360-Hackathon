/**
 * Gencin ana sayfasının kararları (docs/kimlik-ve-dongu.md § 7). Saf
 * fonksiyonlar; testleri genc-paneli.test.ts'de.
 *
 * Sayfa "şimdi ne yapmalıyım" sorusuyla dizilir: önce gencin yanıtını bekleyen
 * işler, sonra fırsatlar; ilişkilerin durumu (ilgi → karşılıklı ilgi → iş
 * birliği) tek bir "Süreçlerin" listesinde, her satırda tek etiketle.
 */

import type {
  BanaGelenIlgi,
  GencEslesmesi,
  IsbirligiOzeti,
  MeYaniti,
} from "@/lib/api";
import { gencDurumEtiketi } from "@/lib/ilgi";
import { EKSIK_ALAN_ETIKETLERI } from "@/lib/profil";
import { ISBIRLIGI_DURUM_ETIKETLERI } from "@/lib/takip";
import { kartYolu } from "@/lib/yonlendirme";

export type Bekleyenler = {
  /** Firma ilgileniyor, gencin kabul ya da reddi bekleniyor. */
  ilgiler: BanaGelenIlgi[];
  /** Planı onay bekleyen iş birlikleri. */
  planlar: IsbirligiOzeti[];
  /** Gecikmiş adımı olan süren iş birlikleri. */
  gecikenler: IsbirligiOzeti[];
};

export function bekleyenler(
  gelenler: BanaGelenIlgi[],
  isbirlikleri: IsbirligiOzeti[],
): Bekleyenler {
  return {
    ilgiler: gelenler.filter((ilgi) => ilgi.durum === "ilgileniliyor"),
    planlar: isbirlikleri.filter((i) => i.durum === "plan_bekliyor"),
    gecikenler: isbirlikleri.filter(
      (i) => i.durum === "aktif" && i.ilerleme.geciken > 0,
    ),
  };
}

export function bekleyenSayisi(b: Bekleyenler): number {
  return b.ilgiler.length + b.planlar.length + b.gecikenler.length;
}

export type SurecSatiri = {
  anahtar: string;
  firma: string;
  dogrulandi: boolean;
  etiket: string;
  /** Bağlantı rengi: karşılıklı ilgi ve iş birliği anları. */
  baglanti: boolean;
  /** Satıra tıklayınca gidilecek yer (iş birliği); yoksa satır düz metin. */
  hedef: string | null;
  /** Gencin geri çekebileceği kendi ilgisi. */
  geriCekilebilir: GencEslesmesi | null;
  tarih: string;
};

/**
 * Gencin bütün ilişkileri tek listede, en yeni önce. Firmanın yanıt beklenen
 * ilgisi burada değil, "Seni bekleyenler"de. İş birliğine dönüşmüş ilgi
 * iki kez görünmez: iş birliği satırı onu temsil eder.
 */
export function surecler(
  ilgilerim: GencEslesmesi[],
  gelenler: BanaGelenIlgi[],
  isbirlikleri: IsbirligiOzeti[],
): SurecSatiri[] {
  const satirlar: SurecSatiri[] = [];
  for (const ilgi of ilgilerim) {
    if (ilgi.isbirligi_id) continue;
    satirlar.push({
      anahtar: ilgi.eslesme_id,
      firma: ilgi.ihtiyac_karti.kurum.ad,
      dogrulandi: ilgi.ihtiyac_karti.kurum.dogrulandi,
      etiket: gencDurumEtiketi(ilgi.durum),
      baglanti: false,
      hedef: null,
      geriCekilebilir: ilgi.durum === "genc_ilgilendi" ? ilgi : null,
      tarih: ilgi.son_aktivite_tarihi,
    });
  }
  for (const ilgi of gelenler) {
    if (ilgi.isbirligi_id || ilgi.durum === "ilgileniliyor") continue;
    satirlar.push({
      anahtar: ilgi.eslesme_id,
      firma: ilgi.ihtiyac_karti.kurum.ad,
      dogrulandi: ilgi.ihtiyac_karti.kurum.dogrulandi,
      etiket: gencDurumEtiketi(ilgi.durum),
      baglanti: false,
      hedef: null,
      geriCekilebilir: null,
      tarih: ilgi.son_aktivite_tarihi,
    });
  }
  for (const isbirligi of isbirlikleri) {
    satirlar.push({
      anahtar: isbirligi.isbirligi_id,
      firma: isbirligi.kurum_adi,
      dogrulandi: false,
      etiket:
        ISBIRLIGI_DURUM_ETIKETLERI[isbirligi.durum] ?? "İş birliği",
      baglanti: isbirligi.durum === "aktif" || isbirligi.durum === "tamamlandi",
      hedef: `/isbirligi/${isbirligi.isbirligi_id}`,
      geriCekilebilir: null,
      tarih: isbirligi.baslangic_tarihi ?? "",
    });
  }
  return satirlar.sort((a, b) => b.tarih.localeCompare(a.tarih));
}

export type EksikAdim = { anahtar: string; metin: string; href: string; etiket: string };

/** Eşleştirmenin kullandığı tercihler; kart sayfasında düzenlenir (docs/kararlar.md G10). */
const TERCIH_ALANLARI = ["sehir", "calisma_modelleri", "musaitlikler"];

/**
 * Engellemeyen eksikler (G10): kart, çalışma tercihleri, hesap bilgileri ve
 * KVKK. Her biri tek satır ve tek eylem; e-posta doğrulaması kendi bandında.
 */
export function eksikAdimlar(
  hesap: Pick<
    MeYaniti,
    "rol" | "yetenek_karti" | "eksik_profil_alanlari" | "kvkk_onayli"
  >,
): EksikAdim[] {
  if (hesap.rol !== "genc") return [];
  const adimlar: EksikAdim[] = [];
  const ad = (alan: string) => EKSIK_ALAN_ETIKETLERI[alan] ?? alan;
  const tercihler = hesap.eksik_profil_alanlari.filter((a) =>
    TERCIH_ALANLARI.includes(a),
  );
  const digerleri = hesap.eksik_profil_alanlari.filter(
    (a) => !TERCIH_ALANLARI.includes(a),
  );
  if (!hesap.yetenek_karti) {
    adimlar.push({
      anahtar: "kart",
      metin: "Kartını oluştur, firmalar seni görebilsin.",
      href: kartYolu(null),
      etiket: "Kartını oluştur",
    });
  } else if (tercihler.length > 0) {
    adimlar.push({
      anahtar: "tercihler",
      metin: `Çalışma tercihlerin eksik: ${tercihler.map(ad).join(", ")}.`,
      href: `${kartYolu(hesap.yetenek_karti)}#tercihler`,
      etiket: "Tercihlerini tamamla",
    });
  }
  if (digerleri.length > 0 || !hesap.kvkk_onayli) {
    const parcalar = [
      ...(digerleri.length > 0 ? [digerleri.map(ad).join(", ")] : []),
      ...(hesap.kvkk_onayli ? [] : ["KVKK onayı"]),
    ];
    adimlar.push({
      anahtar: "hesap",
      metin: `Hesabında eksik: ${parcalar.join(", ")}.`,
      href: "/profil",
      etiket: "Hesabını tamamla",
    });
  }
  return adimlar;
}

/** Sayfa başlığının altındaki tek cümle: en önemli durum. */
export function ozetCumlesi(
  bekleyen: number,
  firsat: number | null,
  kartVar: boolean,
): string {
  if (!kartVar) return "Kartını oluşturduğunda sana uygun fırsatlar burada görünür.";
  if (bekleyen > 0) return `Yanıtını bekleyen ${bekleyen} iş var.`;
  if (firsat && firsat > 0) return `Kartına uyan ${firsat} fırsat var.`;
  return "Kartını güçlendirdikçe yeni fırsatlar gelir.";
}
