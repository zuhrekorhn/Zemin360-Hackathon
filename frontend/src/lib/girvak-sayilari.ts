/**
 * "Platform sayıları" sayfasının içeriği: backend'in `GET /girvak/sayilar` yanıtını
 * başlıklı gruplara çevirir. Saf; yeni bir sayı eklemek tek satırdır, sayfa değişmez.
 */

import type { GirvakSayilari } from "@/lib/api";

export type SayiOgesi = { etiket: string; sayi: number };
export type SayiGrubu = {
  kimlik: string;
  baslik: string;
  aciklama?: string;
  ogeler: SayiOgesi[];
};

export type HuniAdimi = {
  etiket: string;
  sayi: number;
  /** Çubuk genişliği, ilk adıma göre (0-100). */
  genislik: number;
  /** Bir önceki adıma göre yüzde; ilk adımda null. */
  oncekineGore: number | null;
};

/**
 * Eşleşmenin yolu: önerilen → iki tarafın da ilgilendiği → açılan iş birliği →
 * tamamlanan. Öneri sayısı bütün eşleşme durumlarının toplamıdır (reddedilen ve
 * kapananlar dahil: "kaç öneri yapıldı").
 */
export function huniAdimlari(s: GirvakSayilari): HuniAdimi[] {
  const e = s.eslesme;
  const oneri =
    e.onerildi +
    e.ilgileniliyor +
    e.genc_ilgilendi +
    e.kabul_edildi +
    e.reddedildi +
    e.kapandi;
  const adimlar = [
    { etiket: "Önerildi", sayi: oneri },
    { etiket: "İki taraf da ilgilendi", sayi: e.kabul_edildi },
    { etiket: "İş birliği açıldı", sayi: s.isbirligi },
    { etiket: "Tamamlandı", sayi: s.isbirligi_durumlari.tamamlandi },
  ];
  return adimlar.map((a, i) => ({
    ...a,
    genislik: oneri > 0 ? Math.min(100, Math.round((a.sayi / oneri) * 100)) : 0,
    oncekineGore:
      i === 0
        ? null
        : adimlar[i - 1].sayi > 0
          ? Math.min(100, Math.round((a.sayi / adimlar[i - 1].sayi) * 100))
          : null,
  }));
}

export function sayiGruplari(s: GirvakSayilari): SayiGrubu[] {
  return [
    {
      kimlik: "hesaplar",
      baslik: "Hesaplar ve kartlar",
      ogeler: [
        { etiket: "Genç hesabı", sayi: s.hesap.genc },
        { etiket: "Firma hesabı", sayi: s.hesap.kurum },
        { etiket: "Yetenek kartı", sayi: s.yetenek_karti },
        {
          etiket: "Tanımlanan ihtiyaç (kapananlar dahil)",
          sayi: s.ihtiyac_karti,
        },
      ],
    },
    {
      kimlik: "eslesmeler",
      baslik: "Eşleşmeler ve iş birlikleri",
      aciklama:
        "Bir eşleşmenin yolu: öneri, ilgi, karşılıklı ilgi, iş birliği, tamamlanma.",
      ogeler: [
        { etiket: "Önerildi", sayi: s.eslesme.onerildi },
        { etiket: "Adayın yanıtı bekleniyor", sayi: s.eslesme.ilgileniliyor },
        {
          etiket: "Karşılıklı ilgi (kabul edildi)",
          sayi: s.eslesme.kabul_edildi,
        },
        { etiket: "Reddedildi", sayi: s.eslesme.reddedildi },
        { etiket: "Açılan iş birliği", sayi: s.isbirligi },
        {
          etiket: "Plan onayı bekleyen",
          sayi: s.isbirligi_durumlari.plan_bekliyor,
        },
        { etiket: "Süren iş birliği", sayi: s.isbirligi_durumlari.aktif },
        {
          etiket: "Tamamlanan iş birliği",
          sayi: s.isbirligi_durumlari.tamamlandi,
        },
      ],
    },
    {
      kimlik: "kirilim",
      baslik: "Eşleşme türüne göre",
      aciklama:
        "Aynı sayıların iki türe göre dağılımı: genç–firma (firma genç arıyor) ve firma–firma (firma iş birliği ortağı arıyor).",
      ogeler: [
        {
          etiket: "Genç–firma karşılıklı ilgi",
          sayi: s.kirilim.genc_firma.karsilikli_ilgi,
        },
        {
          etiket: "Genç–firma iş birliği",
          sayi: s.kirilim.genc_firma.isbirligi,
        },
        {
          etiket: "Genç–firma tamamlanan iş birliği",
          sayi: s.kirilim.genc_firma.tamamlanan,
        },
        { etiket: "Firma–firma öneri", sayi: s.kirilim.firma_firma.oneri },
        {
          etiket: "Firma–firma karşılıklı ilgi",
          sayi: s.kirilim.firma_firma.karsilikli_ilgi,
        },
        {
          etiket: "Firma–firma iş birliği",
          sayi: s.kirilim.firma_firma.isbirligi,
        },
        {
          etiket: "Firma–firma tamamlanan iş birliği",
          sayi: s.kirilim.firma_firma.tamamlanan,
        },
      ],
    },
    {
      kimlik: "kapananlar",
      baslik: "Kapanan ihtiyaçlar",
      aciklama:
        "Firmalar bir ihtiyacı kapatırken nedenini seçer; nedeni yalnızca siz görürsünüz. “Zemin360'ta bulundu”: firma aradığını burada buldu.",
      ogeler: [
        {
          etiket: "Zemin360'ta bulundu",
          sayi: s.kapanan_ihtiyaclar.platformda_bulundu,
        },
        {
          etiket: "Başka yoldan bulundu",
          sayi: s.kapanan_ihtiyaclar.baska_yoldan_bulundu,
        },
        { etiket: "Vazgeçildi", sayi: s.kapanan_ihtiyaclar.vazgecildi },
        {
          etiket: "Yanlış ya da eksik girildi",
          sayi: s.kapanan_ihtiyaclar.hatali_girildi,
        },
      ],
    },
  ];
}
