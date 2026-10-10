"use client";

import { ChevronDown } from "lucide-react";
import { useId, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * Açılır bölüm: sayfada yalnızca güncel işler görünür, biten kayıtlar (kapanan
 * ihtiyaçlar, tamamlanan iş birlikleri) başlığın arkasında durur ve geçmişe
 * erişim korunur. `acik`: ilk durum (güncel iş kalmadıysa bitenler açık gelir).
 * `listeSinifi`: içerideki listenin yerleşimi.
 */
export function KapaliBolum({
  baslik,
  sayi,
  acik: ilkDurum = false,
  listeSinifi = "flex flex-col gap-4",
  children,
}: {
  baslik: string;
  sayi: number;
  acik?: boolean;
  listeSinifi?: string;
  children: React.ReactNode;
}) {
  const [acik, setAcik] = useState(ilkDurum);
  const listeId = useId();
  return (
    <section aria-label={baslik} className="flex flex-col gap-4">
      <button
        type="button"
        aria-expanded={acik}
        aria-controls={listeId}
        onClick={() => setAcik((onceki) => !onceki)}
        className="inline-flex w-fit items-center gap-1.5 rounded-md text-sm font-medium text-muted-foreground outline-none hover:text-metin focus-visible:ring-3 focus-visible:ring-baglanti/40"
      >
        {baslik} ({sayi})
        <ChevronDown
          aria-hidden="true"
          className={cn("size-4 transition-transform", acik && "rotate-180")}
        />
      </button>
      {acik ? (
        <ul id={listeId} className={listeSinifi}>
          {children}
        </ul>
      ) : null}
    </section>
  );
}
