/**
 * Firma panelinin kararları (docs/kimlik-ve-dongu.md § 7). Saf fonksiyonlar;
 * testleri kurum-paneli.test.ts'de. Gencin ana sayfasıyla (lib/genc-paneli.ts)
 * aynı sıra: önce firmanın yanıtını bekleyen işler, sonra ihtiyaçlar; adayların
 * durumu tek listede, her satırda tek etiketle. Metinler firmaya "siz".
 */

import type { IsbirligiOzeti, KurumOnerisi, MeYaniti } from "@/lib/api";
import { firmaKartiCagrisi } from "@/lib/firma-karti";
import { firmaProfilBandi } from "@/lib/firma-profil";
import { firmaDurumEtiketi } from "@/lib/ilgi";
import type { EksikAdim } from "@/lib/genc-paneli";

export type KurumBekleyenleri = {
  /** Gencin (ya da ortak firmanın) ilgisi geldi; firmanın "İlgileniyorum" ya da "Şimdilik değil"i bekleniyor. */
  ilgiler: KurumOnerisi[];
  /** Planı onay bekleyen iş birlikleri. */
  planlar: IsbirligiOzeti[];
  /** Gecikmiş adımı olan süren iş birlikleri. */
  gecikenler: IsbirligiOzeti[];
};

export function kurumBekleyenleri(
  oneriler: KurumOnerisi[],
  isbirlikleri: IsbirligiOzeti[],
): KurumBekleyenleri {
  return {
    ilgiler: oneriler.filter((o) => o.durum === "genc_ilgilendi"),
    planlar: isbirlikleri.filter(
      // Yalnızca planı henüz onaylamamış taraf bekleniyor sayılır.
      (i) => i.durum === "plan_bekliyor" && !i.planimi_onayladim,
    ),
    gecikenler: isbirlikleri.filter(
      (i) => i.durum === "aktif" && i.ilerleme.geciken > 0,
    ),
  };
}

/**
 * İhtiyaç başına tamamlanan iş birliği sayısı (iş birliği → eşleşme → ihtiyaç).
 * İhtiyaç, bir iş birliği tamamlansa da kendiliğinden kapanmaz (daha fazla ortak
 * gerekebilir); kart bunu söyler ve kapatmayı hatırlatır.
 */
export function tamamlananIsbirligiSayilari(
  oneriler: KurumOnerisi[],
  isbirlikleri: IsbirligiOzeti[],
): Record<string, number> {
  const ihtiyacBasina = new Map(
    oneriler.map((o) => [o.eslesme_id, o.ihtiyac_karti_id]),
  );
  const sayilar: Record<string, number> = {};
  for (const isbirligi of isbirlikleri) {
    if (isbirligi.durum !== "tamamlandi") continue;
    const ihtiyac = ihtiyacBasina.get(isbirligi.eslesme_id);
    if (ihtiyac) sayilar[ihtiyac] = (sayilar[ihtiyac] ?? 0) + 1;
  }
  return sayilar;
}

export function kurumBekleyenSayisi(b: KurumBekleyenleri): number {
  return b.ilgiler.length + b.planlar.length + b.gecikenler.length;
}

/** Bir ihtiyacın sayıları: "3 aday · 1 ilgi". Kapanmış eşleşmeler sayılmaz. */
export type IhtiyacSayilari = { aday: number; ilgi: number };

export function ihtiyacSayilari(
  oneriler: KurumOnerisi[],
): Record<string, IhtiyacSayilari> {
  const sayilar: Record<string, IhtiyacSayilari> = {};
  for (const oneri of oneriler) {
    if (oneri.durum === "reddedildi" || oneri.durum === "kapandi") continue;
    const sayi = (sayilar[oneri.ihtiyac_karti_id] ??= { aday: 0, ilgi: 0 });
    sayi.aday += 1;
    if (oneri.durum === "genc_ilgilendi") sayi.ilgi += 1;
  }
  return sayilar;
}

/** İhtiyaç satırının altındaki sayım; hiç aday yoksa boş. */
export function sayimMetni(sayi: IhtiyacSayilari | undefined): string | null {
  if (!sayi || sayi.aday === 0) return null;
  return sayi.ilgi > 0
    ? `${sayi.aday} aday · ${sayi.ilgi} ilgi gösterdi`
    : `${sayi.aday} aday`;
}

export type AdaySatiri = {
  anahtar: string;
  ad: string;
  /** Genç adayda rolü, firma adayda "Firma". */
  alt: string;
  /** Durum etiketi; yalnızca bir şey söylüyorsa. Listenin kendisi "Adaylarınız" olduğu için "Aday" tekrarlanmaz. */
  etiket: string | null;
  /** Bağlantı rengi: karşılıklı ilgi ve ilgi anları. */
  baglanti: boolean;
  /** Adayın olduğu ihtiyacın aday sayfası. */
  hedef: string;
  tarih: string;
};

/** Kenar sütunundaki liste en çok bu kadar satır gösterir; kalanı ihtiyaç sayfalarında. */
export const ADAY_LISTESI_SINIRI = 6;

/**
 * Bütün adaylar tek listede, en son hareket olan önce. Kapanmış eşleşmeler
 * ("Kapandı") listeyi doldurmasın diye sona atılır.
 */
export function adaySatirlari(oneriler: KurumOnerisi[]): AdaySatiri[] {
  const kapali = (o: KurumOnerisi) =>
    o.durum === "reddedildi" || o.durum === "kapandi";
  const sirali = [...oneriler].sort((a, b) => {
    if (kapali(a) !== kapali(b)) return kapali(a) ? 1 : -1;
    return b.son_aktivite_tarihi.localeCompare(a.son_aktivite_tarihi);
  });
  return sirali.map((oneri) => ({
    anahtar: oneri.eslesme_id,
    ad: oneri.aday_adi,
    alt: oneri.rol_alani ?? "Firma",
    etiket: oneri.durum === "onerildi" ? null : firmaDurumEtiketi(oneri.durum),
    baglanti:
      oneri.durum === "kabul_edildi" || oneri.durum === "genc_ilgilendi",
    hedef: `/kurum/oneriler?ihtiyac=${oneri.ihtiyac_karti_id}`,
    tarih: oneri.son_aktivite_tarihi,
  }));
}

/** Engellemeyen eksikler: firma kartı ve profil. Her biri tek cümle, tek bağlantı. */
export function firmaEksikAdimlari(hesap: MeYaniti): EksikAdim[] {
  const adimlar: EksikAdim[] = [];
  const kart = firmaKartiCagrisi(hesap);
  if (kart)
    adimlar.push({
      anahtar: "firma-karti",
      metin: kart,
      href: "/kurum/kart",
      etiket: "Firma kartını oluştur",
    });
  const profil = firmaProfilBandi(hesap);
  if (profil)
    adimlar.push({
      anahtar: "profil",
      metin: profil,
      href: "/kurum/profil",
      etiket: "Firma profiline git",
    });
  return adimlar;
}

/** Sayfa başlığının altındaki tek cümle: en önemli durum. */
export function kurumOzetCumlesi(
  bekleyen: number,
  acikIhtiyac: number,
  aday: number | null,
): string {
  if (acikIhtiyac === 0)
    return "İlk ihtiyacınızı tanımladığınızda uygun adaylar burada görünür.";
  if (bekleyen > 0) return `Yanıtınızı bekleyen ${bekleyen} iş var.`;
  if (aday && aday > 0) return `İhtiyaçlarınıza uyan ${aday} aday var.`;
  return "İhtiyaçlarınız, adaylarınız ve iş birlikleriniz burada.";
}
