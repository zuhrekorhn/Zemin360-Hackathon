"use client";

import Link from "next/link";

import { PanelBolumu } from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { KUTU } from "@/components/ui/yuzey";
import { girvakFirmalar, girvakIncelemeler } from "@/lib/api";
import { useYukle } from "@/lib/yukle";
import { cn } from "@/lib/utils";

/**
 * Genel bakışta "sizi bekleyen" kutusu: karar sayıları, ayrıntı Karar bekleyenler
 * sayfasında. Hiçbir şey beklemiyorsa tek cümle.
 */
export function BekleyenlerKutusu() {
  const firmalar = useYukle(girvakFirmalar);
  const incelemeler = useYukle(girvakIncelemeler);

  const hata = firmalar.hata ?? incelemeler.hata;
  if (hata) {
    return (
      <HataKutusu
        hata={hata}
        tekrarDene={() => {
          void firmalar.yenile();
          void incelemeler.yenile();
        }}
      />
    );
  }
  if (firmalar.veri === null || incelemeler.veri === null) return null;

  const kalemler = [
    { sayi: firmalar.veri.length, etiket: "firma onayınızı bekliyor" },
    { sayi: incelemeler.veri.length, etiket: "işaret incelemenizi bekliyor" },
  ].filter((k) => k.sayi > 0);

  return (
    <PanelBolumu id="bekleyenler" baslik="Sizi bekleyenler">
      <div
        className={cn(
          KUTU,
          kalemler.length > 0 && "border-l-[3px] border-l-vurgu",
          "flex flex-wrap items-center gap-x-6 gap-y-3 px-6 py-5",
        )}
      >
        {kalemler.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Şu an karar bekleyen bir şey yok.
          </p>
        ) : (
          <>
            <ul className="flex flex-col gap-1">
              {kalemler.map((k) => (
                <li key={k.etiket} className="text-sm">
                  <span className="font-mono text-lg text-ana">{k.sayi}</span>{" "}
                  {k.etiket}
                </li>
              ))}
            </ul>
            <Link
              href="/girvak/kararlar"
              className="ml-auto text-sm font-medium text-baglanti underline underline-offset-4"
            >
              Kararları gör
            </Link>
          </>
        )}
      </div>
    </PanelBolumu>
  );
}
