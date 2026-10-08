import { Check } from "lucide-react";

import { KUTU } from "@/components/ui/yuzey";
import type { ToplananBilgi } from "@/lib/kesif";
import { cn } from "@/lib/utils";

/**
 * Sohbet sürerken "neyin toplandığı" kutusu: başlık, zorunlu alanlarda ilerleme
 * çubuğu ve her bilgi için işaret. Üç sohbet (Keşif, İhtiyaç, Firma kartı)
 * aynı kutuyu kullanır; neyin toplanacağı lib/kesif.ts ve lib/sohbet-onizleme.ts'de.
 */
export function ToplananlarKutusu({
  baslik,
  ilerlemeEtiketi,
  bilgiler,
}: {
  baslik: string;
  /** Ekran okuyucu için: "Kartın ne kadarı hazır". */
  ilerlemeEtiketi: string;
  bilgiler: ToplananBilgi[];
}) {
  const zorunlu = bilgiler.filter((b) => !b.istegeBagli);
  const tamam = zorunlu.filter((b) => b.tamam).length;

  return (
    <section className={cn(KUTU, "flex flex-col gap-3 px-5 py-5")}>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="font-heading text-base font-semibold text-ana">
          {baslik}
        </h2>
        <span className="text-xs text-muted-foreground">
          {tamam}/{zorunlu.length}
        </span>
      </div>
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={zorunlu.length}
        aria-valuenow={tamam}
        aria-label={ilerlemeEtiketi}
        className="h-1.5 overflow-hidden rounded-full bg-kenar"
      >
        <div
          className="h-full rounded-full bg-baglanti transition-[width] duration-500"
          style={{ width: `${(tamam / zorunlu.length) * 100}%` }}
        />
      </div>
      <ul className="flex flex-col gap-2">
        {bilgiler.map((bilgi) => (
          <li key={bilgi.anahtar} className="flex items-center gap-2.5 text-sm">
            <span
              aria-hidden="true"
              className={cn(
                "flex size-5 shrink-0 items-center justify-center rounded-full",
                bilgi.tamam
                  ? "bg-baglanti text-zemin"
                  : "border border-dashed border-kenar",
              )}
            >
              {bilgi.tamam ? <Check className="size-3" /> : null}
            </span>
            <span
              className={bilgi.tamam ? "text-metin" : "text-muted-foreground"}
            >
              {bilgi.etiket}
              {bilgi.istegeBagli ? (
                <span className="text-muted-foreground"> (isteğe bağlı)</span>
              ) : null}
            </span>
            <span className="sr-only">
              {bilgi.tamam ? ", toplandı" : ", bekleniyor"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
