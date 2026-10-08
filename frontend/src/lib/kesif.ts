/**
 * Keşif sohbetinin canlı önizlemesi (docs/agent-specs.md § 1): sohbet sürerken
 * kartta neyin toplandığı. Backend her turda taslağı döndürüyor; genç ne
 * sorulacağını ve ne kadar kaldığını görsün diye. Saf; testi kesif.test.ts'de.
 */

import type { KartTaslagi } from "@/lib/api";

export type ToplananBilgi = {
  anahtar: string;
  etiket: string;
  tamam: boolean;
  istegeBagli?: boolean;
};

export function toplananlar(taslak: KartTaslagi | null): ToplananBilgi[] {
  const ciktilar = taslak?.somut_ciktilar ?? [];
  return [
    { anahtar: "rol", etiket: "Rolün", tamam: Boolean(taslak?.rol_alani) },
    {
      anahtar: "arac",
      etiket: "Kullandığın araçlar",
      tamam: (taslak?.araclar_teknolojiler.length ?? 0) > 0,
    },
    { anahtar: "calisma", etiket: "Bir çalışman", tamam: ciktilar.length > 0 },
    {
      anahtar: "sonuc",
      etiket: "Çalışmanın sonucu",
      tamam: ciktilar.some((c) => Boolean(c.olculebilir_sonuc)),
    },
    {
      anahtar: "pay",
      etiket: "Çalışmadaki payın",
      tamam: ciktilar.some((c) => Boolean(c.kendi_rolu)),
    },
    {
      anahtar: "kanit",
      etiket: "Kanıt linki ya da referans",
      tamam: ciktilar.some((c) => Boolean(c.kanit_linki || c.referans_email)),
      istegeBagli: true,
    },
  ];
}
