/**
 * İki kapı: genç (ana renk) ve firma (vurgu rengi). Hero'da iki satırlı
 * kart-buton, kapanışta tek satırlı buton; hedefler aynı.
 *
 * Vurgu (#B8823C) üstünde beyaz metin 3.3:1'de kalıyor; kontrast renk
 * sadakatinden önce geldiği için firma kapısında koyu metin (4.9:1) —
 * shadcn'deki primary-foreground ile aynı karar.
 */

import Link from "next/link";

import { KAPILAR } from "@/content/landing";
import { cn } from "@/lib/utils";

import { ODAK, ODAK_KOYU } from "./ortak";

export function HeroKapilari() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 sm:gap-3.5">
      <Link
        href={KAPILAR.genc.hedef}
        className={cn(
          "flex flex-col gap-1 rounded-[14px] bg-ana px-5 py-4 text-zemin transition-colors hover:bg-ana/90 sm:py-[18px]",
          ODAK,
        )}
      >
        <span className="text-[17px] font-semibold">{KAPILAR.genc.baslik}</span>
        <span className="text-sm text-zemin/80">{KAPILAR.genc.alt}</span>
      </Link>
      <Link
        href={KAPILAR.firma.hedef}
        className={cn(
          "flex flex-col gap-1 rounded-[14px] bg-vurgu px-5 py-4 text-metin transition-colors hover:bg-vurgu/90 sm:py-[18px]",
          ODAK,
        )}
      >
        <span className="text-[17px] font-semibold">
          {KAPILAR.firma.baslik}
        </span>
        <span className="text-sm">{KAPILAR.firma.alt}</span>
      </Link>
    </div>
  );
}

/** Koyu (ana) blok üstünde; açık buton zemin rengi. */
export function KapanisKapilari() {
  const ortak =
    "inline-flex h-14 w-full items-center justify-center rounded-xl px-6 text-center text-[17px] font-semibold transition-colors sm:w-[340px]";
  return (
    <div className="flex flex-col gap-3.5 lg:items-end">
      <Link
        href={KAPILAR.genc.hedef}
        className={cn(ortak, "bg-zemin text-metin hover:bg-card", ODAK_KOYU)}
      >
        {KAPILAR.genc.baslik}
      </Link>
      <Link
        href={KAPILAR.firma.hedef}
        className={cn(ortak, "bg-vurgu text-metin hover:bg-vurgu/90", ODAK_KOYU)}
      >
        {KAPILAR.firma.baslik}
      </Link>
    </div>
  );
}
