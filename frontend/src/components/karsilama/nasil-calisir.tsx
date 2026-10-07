"use client";

/**
 * "Nasıl çalışır" bölümü: genç (sen) / firma (siz) sekmeleri.
 *
 * Erişilebilir sekme listesi: yalnızca seçili sekme Tab sırasında, oklar,
 * Home ve End ile gezinilir (lib/sekme.ts). Menüdeki "Gençler için / Firmalar
 * için" SEKME_OLAYI ile burada sekme seçer; kaydırmayı bağlantı yapar.
 */

import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { NASIL, type Sekme } from "@/content/landing";
import { klavyeyleSekme } from "@/lib/sekme";
import { cn } from "@/lib/utils";

import { KAPSAYICI, ODAK, SEKME_OLAYI, UST_ETIKET } from "./ortak";

export function NasilCalisir() {
  const [secili, setSecili] = useState<Sekme>("genc");
  const dugmeler = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    const dinle = (olay: Event) => {
      const sekme = (olay as CustomEvent<Sekme>).detail;
      if (sekme === "genc" || sekme === "firma") setSecili(sekme);
    };
    window.addEventListener(SEKME_OLAYI, dinle);
    return () => window.removeEventListener(SEKME_OLAYI, dinle);
  }, []);

  const tusaBasildi = (olay: KeyboardEvent<HTMLDivElement>) => {
    const anlik = NASIL.sekmeler.findIndex((s) => s.deger === secili);
    const yeni = klavyeyleSekme(anlik, olay.key, NASIL.sekmeler.length);
    if (yeni === null) return;
    olay.preventDefault();
    setSecili(NASIL.sekmeler[yeni].deger);
    dugmeler.current[yeni]?.focus();
  };

  return (
    <section
      id="nasil"
      aria-labelledby="nasil-baslik"
      className="scroll-mt-16 lg:scroll-mt-[77px] py-16 sm:py-24 lg:py-28"
    >
      <div className={cn(KAPSAYICI, "flex flex-col gap-8 lg:gap-11")}>
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between md:gap-10">
          <div className="flex flex-col gap-3">
            <p className={UST_ETIKET}>{NASIL.ustEtiket}</p>
            <h2
              id="nasil-baslik"
              className="font-heading text-[28px] leading-[1.1] font-semibold text-ana lg:text-[44px]"
            >
              {NASIL.baslik}
            </h2>
          </div>

          <div
            role="tablist"
            aria-labelledby="nasil-baslik"
            onKeyDown={tusaBasildi}
            className="flex shrink-0 gap-1 self-start rounded-xl bg-muted p-[5px] md:self-auto"
          >
            {NASIL.sekmeler.map((sekme, i) => {
              const aktif = sekme.deger === secili;
              return (
                <button
                  key={sekme.deger}
                  ref={(el) => {
                    dugmeler.current[i] = el;
                  }}
                  type="button"
                  role="tab"
                  id={`nasil-sekme-${sekme.deger}`}
                  aria-selected={aktif}
                  aria-controls="nasil-panel"
                  tabIndex={aktif ? 0 : -1}
                  onClick={() => setSecili(sekme.deger)}
                  className={cn(
                    "h-11 rounded-[9px] px-5 text-[15px] transition-colors",
                    aktif
                      ? "bg-card font-semibold text-metin shadow-sm"
                      : "font-medium text-muted-foreground hover:text-ana",
                    ODAK,
                  )}
                >
                  {sekme.etiket}
                </button>
              );
            })}
          </div>
        </div>

        <div
          id="nasil-panel"
          role="tabpanel"
          aria-labelledby={`nasil-sekme-${secili}`}
        >
          <ol className="grid gap-4 md:grid-cols-3 lg:gap-6">
            {NASIL.adimlar[secili].map((adim, i) => (
              <li
                key={adim.baslik}
                className="flex flex-col gap-3.5 rounded-[18px] border border-kenar bg-card p-6 lg:min-h-[250px] lg:p-8"
              >
                <span
                  aria-hidden="true"
                  className="flex size-10 items-center justify-center rounded-full bg-ana font-heading text-lg font-semibold text-zemin"
                >
                  {i + 1}
                </span>
                <h3 className="text-[19px] leading-snug font-semibold text-metin lg:text-[21px]">
                  {adim.baslik}
                </h3>
                <p className="leading-relaxed text-muted-foreground">
                  {adim.metin}
                </p>
                <p className="mt-auto border-t border-kenar/70 pt-3.5 text-sm text-muted-foreground">
                  {NASIL.sonucEtiketi}{" "}
                  <strong className="font-semibold text-ana">
                    {adim.sonuc}
                  </strong>
                </p>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
