/**
 * GİRVAK paneli: Özet'teki altı ihtiyaç alanı kartları ve İş birlikleri
 * sayfasının filtreleri (docs/canlilik.md § 7). Saf; testi girvak.test.ts'de.
 *
 * Sayılar backend'den (`GET /girvak/ozet`), cümleler burada: rehber kuralı
 * (docs/icerik-rehberi.md, GİRVAK terimleri). Alan adları programın brifindeki
 * adlarla aynı.
 */

import type { GirvakIsbirligi, GirvakOzet } from "@/lib/api";

export type AlanKarti = {
  /** "01" … "06": brifteki ihtiyaç alanı numarası. */
  no: string;
  ad: string;
  /** Büyük görünen ana sayı ("%62", "3"); hesaplanamıyorsa "—". */
  sayi: string;
  /** Sayının yanındaki kısa ad ("çalışma değerlendirildi"). */
  etiket: string;
  aciklama: string;
  /** Ayrıntının bulunduğu sayfa. */
  yol: string;
};

/** Yüzde (0-100, yuvarlanmış); toplam yoksa null. */
export function yuzde(parca: number, toplam: number): number | null {
  if (toplam <= 0) return null;
  return Math.min(100, Math.round((parca / toplam) * 100));
}

/** "%62"; hesaplanamıyorsa "—". */
export function yuzdeMetni(parca: number, toplam: number): string {
  const y = yuzde(parca, toplam);
  return y === null ? "—" : `%${y}`;
}

export function alanKartlari(o: GirvakOzet): AlanKarti[] {
  const { kesif, dogruluk, eslesme, ag, tanim, takip } = o;
  return [
    {
      no: "01",
      ad: "Genç Yeteneklerin Keşfi",
      sayi: String(kesif.kart_olusturan_genc),
      etiket: "genç yetenek kartı oluşturdu",
      aciklama: `${kesif.kayitli_genc} genç kayıtlı; ${kesif.firsat_goren_genc} genç en az bir fırsat gördü.`,
      yol: "/girvak/sayilar",
    },
    {
      no: "02",
      ad: "Profil ve Portfolyo Doğruluğu",
      sayi: yuzdeMetni(dogruluk.degerlendirilen_calisma, dogruluk.calisma),
      etiket: "çalışma değerlendirildi",
      aciklama:
        dogruluk.bekleyen_inceleme > 0
          ? `${dogruluk.degerlendirilen_calisma} / ${dogruluk.calisma} çalışma. ${dogruluk.bekleyen_inceleme} inceleme sizi bekliyor.`
          : `${dogruluk.degerlendirilen_calisma} / ${dogruluk.calisma} çalışma. Bekleyen inceleme yok.`,
      yol: "/girvak/kararlar",
    },
    {
      no: "03",
      ad: "Kurum–Kişi Eşleşmesi",
      sayi: String(eslesme.karsilikli_ilgi),
      etiket: "karşılıklı ilgi",
      aciklama: `${eslesme.oneri_toplam} öneriden ${eslesme.karsilikli_ilgi} tanesinde iki taraf da ilgilendi.`,
      yol: "/girvak/sayilar",
    },
    {
      no: "04",
      ad: "Yaşayan Bir Ağ",
      sayi: String(ag.takilan_surec),
      etiket: "takılan süreç",
      aciklama:
        ag.takilan_surec === 0
          ? `Şu an takılan süreç yok. Son 30 günde ${ag.hatirlatma_30_gun} hatırlatma gönderildi.`
          : `Son 30 günde ${ag.hatirlatma_30_gun} hatırlatma gönderildi.`,
      yol: "/girvak/canlilik",
    },
    {
      no: "05",
      ad: "İhtiyaçların Net Tanımı",
      sayi: String(tanim.ihtiyac),
      etiket: "ihtiyaç tanımlandı",
      aciklama: `${tanim.olculebilir_ihtiyac} tanesinde ölçülebilir bir hedef var.`,
      yol: "/girvak/sayilar",
    },
    {
      no: "06",
      ad: "Şeffaf İş Birliği Takibi",
      sayi: String(takip.isbirligi),
      etiket: "iş birliği",
      aciklama: `${takip.tamamlanan} tamamlandı; ${takip.gecikmis_adim} gecikmiş adım var.`,
      yol: "/girvak/isbirlikleri",
    },
  ];
}

/* --- İş birlikleri sayfası ---------------------------------------------- */

export type IsbirligiFiltresi =
  "hepsi" | "plan_bekliyor" | "suren" | "gecikmis" | "tamamlanan" | "sonlanan";

export const ISBIRLIGI_FILTRELERI: {
  deger: IsbirligiFiltresi;
  etiket: string;
}[] = [
  { deger: "hepsi", etiket: "Hepsi" },
  { deger: "plan_bekliyor", etiket: "Plan onayı bekleyen" },
  { deger: "suren", etiket: "Süren" },
  { deger: "gecikmis", etiket: "Gecikmiş adımı olan" },
  { deger: "tamamlanan", etiket: "Tamamlanan" },
  { deger: "sonlanan", etiket: "Sonlanan" },
];

/** Bir iş birliği filtreye uyuyor mu. "Gecikmiş" süren iş birliklerinin alt kümesi. */
export function filtreyeUyar(
  isbirligi: Pick<GirvakIsbirligi, "durum" | "ilerleme">,
  filtre: IsbirligiFiltresi,
): boolean {
  switch (filtre) {
    case "hepsi":
      return true;
    case "plan_bekliyor":
      return isbirligi.durum === "plan_bekliyor";
    case "suren":
      return isbirligi.durum === "aktif";
    case "gecikmis":
      return isbirligi.durum === "aktif" && isbirligi.ilerleme.geciken > 0;
    case "tamamlanan":
      return isbirligi.durum === "tamamlandi";
    case "sonlanan":
      return isbirligi.durum === "sonlandi";
  }
}

export function filtrele<T extends Pick<GirvakIsbirligi, "durum" | "ilerleme">>(
  liste: T[],
  filtre: IsbirligiFiltresi,
): T[] {
  return liste.filter((i) => filtreyeUyar(i, filtre));
}

/** Her filtre düğmesinin yanındaki sayı. */
export function filtreSayilari(
  liste: Pick<GirvakIsbirligi, "durum" | "ilerleme">[],
): Record<IsbirligiFiltresi, number> {
  return Object.fromEntries(
    ISBIRLIGI_FILTRELERI.map((f) => [f.deger, filtrele(liste, f.deger).length]),
  ) as Record<IsbirligiFiltresi, number>;
}

/** Filtreye uyan iş birlikleri yokken söylenen cümle. */
export function bosFiltreMetni(filtre: IsbirligiFiltresi): string {
  switch (filtre) {
    case "hepsi":
      return "Henüz açılmış bir iş birliği yok. Bir eşleşmede iki taraf da ilgilenince iş birliği burada görünür.";
    case "plan_bekliyor":
      return "Planı onay bekleyen iş birliği yok.";
    case "suren":
      return "Şu an süren bir iş birliği yok.";
    case "gecikmis":
      return "Gecikmiş adımı olan iş birliği yok.";
    case "tamamlanan":
      return "Henüz tamamlanan iş birliği yok.";
    case "sonlanan":
      return "Sonlanan iş birliği yok.";
  }
}
