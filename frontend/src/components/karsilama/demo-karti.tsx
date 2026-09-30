/**
 * Hero'daki örnek akış (brief § 3.2): soru → yanıt → yetenek kartı → fırsat.
 *
 * Sayfadaki tek bilinçli hareket burada (design-language.md): öğeler ~600ms
 * arayla, belirip hafifçe yukarı kayarak gelir. Hareket `motion-safe:` ile
 * sınırlı; reduced-motion açıksa animasyon sınıfı hiç uygulanmaz, her şey
 * baştan görünür. Gecikme satır içi: yalnızca animasyon varken anlamı var.
 */

import type { CSSProperties, ReactNode } from "react";

import { DEMO } from "@/content/landing";
import { cn } from "@/lib/utils";

const BELIRME =
  "motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-500 motion-safe:fill-mode-both";

function Beliren({
  sira,
  className,
  children,
}: {
  sira: number;
  className?: string;
  children: ReactNode;
}) {
  const stil: CSSProperties = { animationDelay: `${300 + sira * 600}ms` };
  return (
    <div className={cn(BELIRME, className)} style={stil}>
      {children}
    </div>
  );
}

export function OrnekRozeti({ children }: { children: ReactNode }) {
  return (
    <span className="shrink-0 rounded-full border border-kenar px-2.5 py-0.5 text-xs font-semibold text-muted-foreground">
      {children}
    </span>
  );
}

export function DemoKarti() {
  return (
    <div className="flex flex-col gap-3.5 rounded-[20px] border border-kenar bg-card p-[18px] shadow-[0_24px_60px_-30px] shadow-metin/35 sm:gap-4 sm:rounded-[22px] sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-ana">{DEMO.baslik}</p>
        <OrnekRozeti>{DEMO.rozet}</OrnekRozeti>
      </div>

      <Beliren
        sira={0}
        className="max-w-[88%] self-start rounded-2xl rounded-bl-[4px] bg-muted px-4 py-3.5 text-[15px] leading-normal text-metin sm:max-w-[82%]"
      >
        {DEMO.soru}
      </Beliren>

      <Beliren
        sira={1}
        className="max-w-[88%] self-end rounded-2xl rounded-br-[4px] bg-ana px-4 py-3.5 text-[15px] leading-normal text-zemin sm:max-w-[82%]"
      >
        {DEMO.yanit}
      </Beliren>

      <Beliren
        sira={2}
        className="flex items-center gap-2.5 text-sm font-semibold text-muted-foreground"
      >
        <span aria-hidden="true" className="h-px grow bg-kenar" />
        <span>{DEMO.ayrac}</span>
        <span aria-hidden="true" className="h-px grow bg-kenar" />
      </Beliren>

      <Beliren
        sira={3}
        className="flex flex-col gap-3 rounded-[14px] border border-kenar bg-card p-4"
      >
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <p className="font-heading text-lg font-semibold text-ana">
            {DEMO.kart.ad}
          </p>
          <p className="text-sm text-muted-foreground">{DEMO.kart.ozet}</p>
        </div>
        <ul className="flex flex-wrap gap-2">
          {DEMO.kart.yetkinlikler.map((yetkinlik) => (
            <li
              key={yetkinlik}
              className="rounded-lg bg-baglanti/12 px-2.5 py-1 text-sm font-medium text-ana"
            >
              {yetkinlik}
            </li>
          ))}
        </ul>
      </Beliren>

      <Beliren
        sira={4}
        className="flex flex-col gap-1.5 rounded-[14px] bg-vurgu/15 p-4"
      >
        <p className="text-sm font-semibold text-ana">{DEMO.firsat.baslik}</p>
        <p className="text-[15px] leading-normal text-metin">
          {DEMO.firsat.metin}
        </p>
      </Beliren>
    </div>
  );
}
