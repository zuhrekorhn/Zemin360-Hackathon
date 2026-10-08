/**
 * Firma sohbetlerinin canlı önizlemesi (Keşif'inkinin eşi, lib/kesif.ts): sohbet
 * sürerken kartta neyin toplandığı. Backend her turda taslağı döndürüyor.
 * Zorunlu alanlar backend'deki sabitlerle aynı (`app/agents/tanimlama.py` ›
 * `ZORUNLU_ALANLAR`, `app/core/firma_karti.py` › `ZORUNLU_ALANLAR`); onay
 * boş zorunlu alanı kabul etmez. Saf; testi sohbet-onizleme.test.ts'de.
 */

import type { FirmaKartiTaslagi, IhtiyacTaslagi } from "@/lib/api";
import type { ToplananBilgi } from "@/lib/kesif";

/** İhtiyaç sohbeti: ortak ilanında çalışma modeli sorulmaz, iş birliği türü sorulur. */
export function ihtiyacToplananlari(
  taslak: IhtiyacTaslagi | null,
  ortak: boolean,
): ToplananBilgi[] {
  const bilgiler: ToplananBilgi[] = [
    {
      anahtar: "problem",
      etiket: "Çözmek istediğiniz problem",
      tamam: Boolean(taslak?.problem_tanimi),
    },
    {
      anahtar: "kriter",
      etiket: "Başarı ölçütü",
      tamam: Boolean(taslak?.basari_kriteri),
    },
    {
      anahtar: "hedef",
      etiket: "Hedef ve süre",
      tamam: Boolean(taslak?.basari_olcutu?.hedef_deger),
      istegeBagli: true,
    },
    {
      anahtar: "kisit",
      etiket: "Kısıtlar",
      tamam: Boolean(taslak?.kisitlar),
      istegeBagli: true,
    },
  ];
  if (ortak)
    bilgiler.push({
      anahtar: "isbirligi",
      etiket: "İş birliği türü",
      tamam: Boolean(taslak?.isbirligi_turu),
      istegeBagli: true,
    });
  return bilgiler;
}

/** Firma kartı sohbeti: kayıtta verilen bilgiler (ad, sektör, şehir) sorulmaz. */
export function firmaKartiToplananlari(
  taslak: FirmaKartiTaslagi | null,
): ToplananBilgi[] {
  return [
    {
      anahtar: "ne",
      etiket: "Ne yaptığınız",
      tamam: Boolean(taslak?.ne_yapiyoruz),
    },
    {
      anahtar: "yetkinlik",
      etiket: "Yetkinlikleriniz",
      tamam: (taslak?.yetkinlikler.length ?? 0) > 0,
    },
    {
      anahtar: "onceki",
      etiket: "Önceki işleriniz",
      tamam: Boolean(taslak?.onceki_isler),
      istegeBagli: true,
    },
    {
      anahtar: "aranan",
      etiket: "Aradığınız ortak",
      tamam: Boolean(taslak?.aranan_isbirligi),
      istegeBagli: true,
    },
  ];
}
