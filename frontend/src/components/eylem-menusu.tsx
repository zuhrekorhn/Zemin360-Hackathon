"use client";

import { MoreHorizontal } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * "⋯" menüsü: bir öğenin ikincil eylemleri (düzenle, sil). Yıkıcı eylem
 * birincil düğmelerle yan yana durmasın diye burada; dışarı tıklayınca ya da
 * Escape'le kapanır.
 */
export function EylemMenusu({
  etiket,
  eylemler,
}: {
  /** Ekran okuyucu için: "“Kütüphane sistemi” için eylemler". */
  etiket: string;
  eylemler: { etiket: string; onSec: () => void; yikici?: boolean }[];
}) {
  const [acik, setAcik] = useState(false);
  const kutu = useRef<HTMLDivElement>(null);
  const dugme = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!acik) return;
    function disari(olay: MouseEvent) {
      if (!kutu.current?.contains(olay.target as Node)) setAcik(false);
    }
    function tus(olay: KeyboardEvent) {
      if (olay.key === "Escape") {
        setAcik(false);
        dugme.current?.focus();
      }
    }
    document.addEventListener("mousedown", disari);
    document.addEventListener("keydown", tus);
    return () => {
      document.removeEventListener("mousedown", disari);
      document.removeEventListener("keydown", tus);
    };
  }, [acik]);

  return (
    <div ref={kutu} className="relative">
      <button
        ref={dugme}
        type="button"
        aria-label={etiket}
        aria-expanded={acik}
        onClick={() => setAcik((onceki) => !onceki)}
        className="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground outline-none hover:bg-muted hover:text-metin focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <MoreHorizontal aria-hidden="true" className="size-4" />
      </button>
      {acik ? (
        <div className="absolute top-full right-0 z-30 mt-1 flex w-40 flex-col rounded-lg border border-kenar bg-card p-1 shadow-[0_8px_24px_-12px_rgb(22_33_27/0.25)]">
          {eylemler.map((eylem) => (
            <button
              key={eylem.etiket}
              type="button"
              onClick={() => {
                setAcik(false);
                eylem.onSec();
              }}
              className={cn(
                "flex min-h-9 items-center rounded-md px-3 text-left text-sm hover:bg-muted",
                eylem.yikici ? "text-destructive" : "text-metin",
              )}
            >
              {eylem.etiket}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
