"use client";

import { FormAlani } from "@/components/sohbet";
import { Input } from "@/components/ui/input";
import type { KartAlanDegerleri } from "@/lib/kart-duzenleme";
import { DENEYIM_ETIKETLERI } from "@/lib/sabitler";

/**
 * Yetenek kartının üst alanları: rol, deneyim, sektör, araçlar, sertifikalar,
 * diller. Kart düzenleme ve Keşif taslağı aynı alanları gösterir; kayıt ve
 * doğrulama çağıranın işi. Rol, deneyim ve sektör zorunlu (onay kuralı).
 */

type ListeAlani = {
  ad: "sektor" | "araclar" | "sertifikalar" | "diller";
  etiket: string;
  ornek: string;
  zorunlu: boolean;
};

const LISTE_ALANLARI: ListeAlani[] = [
  {
    ad: "sektor",
    etiket: "Sektör ilgisi",
    ornek: "ör. eğitim, sivil toplum (virgülle ayır)",
    zorunlu: true,
  },
  {
    ad: "araclar",
    etiket: "Araçlar ve yöntemler",
    ornek: "ör. Python, Figma (virgülle ayır)",
    zorunlu: false,
  },
  {
    ad: "sertifikalar",
    etiket: "Sertifikalar",
    ornek: "ör. Google Analytics sertifikası",
    zorunlu: false,
  },
  {
    ad: "diller",
    etiket: "Diller",
    ornek: "ör. İngilizce (B2)",
    zorunlu: false,
  },
];

const SECIM_SINIFI =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30";

export function KartAlanlari({
  kimlik,
  degerler,
  onDegis,
}: {
  /** Aynı sayfada iki form olursa `id`ler çakışmasın diye önek. */
  kimlik: string;
  degerler: KartAlanDegerleri;
  onDegis: (alan: keyof KartAlanDegerleri, deger: string) => void;
}) {
  return (
    <>
      <FormAlani etiket="Rol / alan" htmlFor={`${kimlik}-rol`}>
        <Input
          id={`${kimlik}-rol`}
          value={degerler.rol}
          required
          placeholder="ör. backend geliştirici, sosyal medya içerik üreticisi"
          onChange={(olay) => onDegis("rol", olay.target.value)}
        />
      </FormAlani>
      <FormAlani etiket="Deneyim" htmlFor={`${kimlik}-deneyim`}>
        <select
          id={`${kimlik}-deneyim`}
          value={degerler.deneyim}
          required
          onChange={(olay) => onDegis("deneyim", olay.target.value)}
          className={SECIM_SINIFI}
        >
          {/* Sohbet seviyeyi netleştiremediyse seçim gencin. */}
          {degerler.deneyim ? null : <option value="">Seç</option>}
          {Object.entries(DENEYIM_ETIKETLERI).map(([deger, etiket]) => (
            <option key={deger} value={deger}>
              {etiket}
            </option>
          ))}
        </select>
      </FormAlani>
      {LISTE_ALANLARI.map(({ ad, etiket, ornek, zorunlu }) => (
        <FormAlani
          key={ad}
          etiket={etiket}
          htmlFor={`${kimlik}-${ad}`}
          istegeBagli={!zorunlu}
        >
          <Input
            id={`${kimlik}-${ad}`}
            value={degerler[ad]}
            required={zorunlu}
            placeholder={ornek}
            onChange={(olay) => onDegis(ad, olay.target.value)}
          />
        </FormAlani>
      ))}
    </>
  );
}
