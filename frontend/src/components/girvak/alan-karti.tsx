import Link from "next/link";

import { KUTU } from "@/components/ui/yuzey";
import type { AlanKarti } from "@/lib/girvak";
import { cn } from "@/lib/utils";

/**
 * Programın bir ihtiyaç alanı: brifteki adıyla başlık, büyük ana sayı ve tek
 * cümlelik durum; ayrıntı ilgili sayfada. Genç panelindeki "Kartının durumu"
 * ile aynı sayı dili (başlık fontu, `KUTU` yüzeyi).
 */
export function AlanKartiOgesi({ alan }: { alan: AlanKarti }) {
  return (
    <li className={cn(KUTU, "flex flex-col gap-3 px-5 py-5")}>
      <div className="flex items-center gap-2.5">
        <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-xs text-muted-foreground">
          {alan.no}
        </span>
        <h3 className="text-sm font-medium text-pretty text-ana">{alan.ad}</h3>
      </div>
      <p className="flex flex-wrap items-baseline gap-x-2">
        <span className="font-heading text-4xl font-semibold text-ana">
          {alan.sayi}
        </span>
        <span className="text-sm text-muted-foreground">{alan.etiket}</span>
      </p>
      <p className="text-sm text-pretty text-muted-foreground">
        {alan.aciklama}
      </p>
      <Link
        href={alan.yol}
        className="mt-auto w-fit text-sm font-medium text-baglanti underline underline-offset-4"
      >
        Ayrıntıya git
      </Link>
    </li>
  );
}
