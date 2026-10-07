"use client";

/**
 * Karşılama sayfasının üst menüsü. Yalnızca / sayfasında ve
 * giriş yapılmamışken UstMenu'nün yerine gösterilir; iskelet (yapışkanlık,
 * katlanır menü) MenuKabugu'nda, uygulama menüsüyle ortak.
 */

import Link from "next/link";

import { MENU_ODAK, MenuKabugu } from "@/components/menu-kabugu";
import { MENU, YOLLAR } from "@/content/landing";
import { cn } from "@/lib/utils";

import { sekmeyiSec } from "./ortak";

export function KarsilamaMenusu() {
  const baglantilar = (ekSinif: string, kapat?: () => void) =>
    MENU.baglantilar.map((baglanti) => (
      <a
        key={baglanti.etiket}
        href={baglanti.hedef}
        onClick={() => {
          if (baglanti.sekme) sekmeyiSec(baglanti.sekme);
          kapat?.();
        }}
        className={cn(
          "inline-flex min-h-11 items-center rounded-sm text-muted-foreground hover:text-ana",
          MENU_ODAK,
          ekSinif,
        )}
      >
        {baglanti.etiket}
      </a>
    ));

  return (
    <MenuKabugu
      ortala
      masaustu={baglantilar("")}
      sag={
        <>
          <Link
            href={YOLLAR.giris}
            className={cn(
              "inline-flex h-11 items-center rounded-lg px-3 font-medium text-metin hover:text-ana lg:px-4",
              MENU_ODAK,
            )}
          >
            {MENU.giris}
          </Link>
          <Link
            href={YOLLAR.kayit}
            className={cn(
              "hidden h-11 items-center rounded-[10px] bg-ana px-5 font-semibold text-zemin hover:bg-ana/90 lg:inline-flex",
              MENU_ODAK,
            )}
          >
            {MENU.kayit}
          </Link>
        </>
      }
      mobil={(kapat) => (
        <>
          {baglantilar("px-1 text-base", kapat)}
          <Link
            href={YOLLAR.kayit}
            onClick={kapat}
            className={cn(
              "mt-3 inline-flex h-12 items-center justify-center rounded-[10px] bg-ana px-5 font-semibold text-zemin hover:bg-ana/90",
              MENU_ODAK,
            )}
          >
            {MENU.kayit}
          </Link>
        </>
      )}
    />
  );
}
