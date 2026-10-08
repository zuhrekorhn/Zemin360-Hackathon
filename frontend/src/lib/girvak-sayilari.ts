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

export function sayiGruplari(s: GirvakSayilari): SayiGrubu[] {
  return [
    {
      kimlik: "hesaplar",
      baslik: "Hesaplar ve kartlar",
      ogeler: [
        { etiket: "Genç hesabı", sayi: s.hesap.genc },
        { etiket: "Firma hesabı", sayi: s.hesap.kurum },
        { etiket: "Yetenek kartı", sayi: s.yetenek_karti },
        { etiket: "İhtiyaç kartı", sayi: s.ihtiyac_karti },
      ],
    },
    {
      kimlik: "eslesmeler",
      baslik: "Eşleşmeler ve iş birlikleri",
      aciklama:
        "Öneriden tamamlanan iş birliğine: firma ilgilenir, genç kabul eder, plan iki tarafça onaylanır ve adım adım tamamlanır.",
      ogeler: [
        { etiket: "Önerildi", sayi: s.eslesme.onerildi },
        { etiket: "Gencin yanıtı bekleniyor", sayi: s.eslesme.ilgileniliyor },
        { etiket: "Kabul edildi", sayi: s.eslesme.kabul_edildi },
        { etiket: "Reddedildi", sayi: s.eslesme.reddedildi },
        { etiket: "İş birliği", sayi: s.isbirligi },
        { etiket: "Planı bekleyen", sayi: s.isbirligi_durumlari.plan_bekliyor },
        { etiket: "Süren iş birliği", sayi: s.isbirligi_durumlari.aktif },
        {
          etiket: "Tamamlanan iş birliği",
          sayi: s.isbirligi_durumlari.tamamlandi,
        },
      ],
    },
    {
      kimlik: "kirilim",
      baslik: "Genç–firma ve firma–firma",
      aciklama:
        "Yukarıdaki toplamların eşleşme türüne göre dağılımı. Firma–firma, bir firmanın iş birliği ortağı aradığı ihtiyaçlardan çıkan eşleşmeler.",
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
          etiket: "Genç–firma tamamlanan",
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
          etiket: "Firma–firma tamamlanan",
          sayi: s.kirilim.firma_firma.tamamlanan,
        },
      ],
    },
    {
      kimlik: "kapananlar",
      baslik: "Kapanan ihtiyaçlar",
      aciklama:
        "Firmaların ihtiyacı kapatırken seçtiği neden. Nedeni yalnızca siz görürsünüz.",
      ogeler: [
        {
          etiket: "Platformda bulundu",
          sayi: s.kapanan_ihtiyaclar.platformda_bulundu,
        },
        {
          etiket: "Başka yoldan bulundu",
          sayi: s.kapanan_ihtiyaclar.baska_yoldan_bulundu,
        },
        { etiket: "Vazgeçildi", sayi: s.kapanan_ihtiyaclar.vazgecildi },
        { etiket: "Yanlış girildi", sayi: s.kapanan_ihtiyaclar.hatali_girildi },
      ],
    },
  ];
}
