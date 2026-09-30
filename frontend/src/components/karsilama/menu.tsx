"use client";

/**
 * Karşılama sayfasının üst menüsü (brief § 3.1). Yalnızca / sayfasında ve
 * giriş yapılmamışken UstMenu'nün yerine gösterilir; diğer sayfalar ve
 * girişli kullanıcı her zamanki menüyü görür.
 *
 * Yapışkan: sayfa uzun, menü kaydırınca kaybolmasın. Bölümlerin scroll-mt
 * değeri menünün yüksekliği (64px, lg'de 76px + çizgi); başlık altında kalmasın.
 */

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { MENU, YOLLAR } from "@/content/landing";
import { cn } from "@/lib/utils";

import { KAPSAYICI, ODAK, sekmeyiSec } from "./ortak";

export function KarsilamaMenusu() {
  const [acik, setAcik] = useState(false);

  const baglantilar = (ekSinif: string, kapat: boolean) =>
    MENU.baglantilar.map((baglanti) => (
      <a
        key={baglanti.etiket}
        href={baglanti.hedef}
        onClick={() => {
          if (baglanti.sekme) sekmeyiSec(baglanti.sekme);
          if (kapat) setAcik(false);
        }}
        className={cn(
          "inline-flex min-h-11 items-center text-muted-foreground hover:text-ana",
          ODAK,
          ekSinif,
        )}
      >
        {baglanti.etiket}
      </a>
    ));

  return (
    <header className="sticky top-0 z-40 border-b border-kenar bg-zemin">
      <nav
        aria-label="Ana menü"
        className={cn(KAPSAYICI, "flex h-16 items-center gap-4 lg:h-[76px]")}
      >
        <Link
          href="/"
          className={cn(
            "mr-auto rounded-sm font-heading text-[21px] font-semibold text-ana lg:mr-0 lg:text-2xl",
            ODAK,
          )}
        >
          {MENU.logo}
        </Link>

        <div className="mx-auto hidden items-center gap-9 lg:flex">
          {baglantilar("rounded-sm", false)}
        </div>

        <div className="flex items-center gap-1 lg:gap-3">
          <Link
            href={YOLLAR.giris}
            className={cn(
              "inline-flex h-11 items-center rounded-lg px-3 font-medium text-metin hover:text-ana lg:px-4",
              ODAK,
            )}
          >
            {MENU.giris}
          </Link>
          <Link
            href={YOLLAR.kayit}
            className={cn(
              "hidden h-11 items-center rounded-[10px] bg-ana px-5 font-semibold text-zemin hover:bg-ana/90 lg:inline-flex",
              ODAK,
            )}
          >
            {MENU.kayit}
          </Link>
          <button
            type="button"
            aria-expanded={acik}
            aria-controls="karsilama-mobil-menu"
            aria-label={acik ? MENU.menuyuKapat : MENU.menuyuAc}
            onClick={() => setAcik((onceki) => !onceki)}
            className={cn(
              "inline-flex size-11 items-center justify-center rounded-lg text-metin lg:hidden",
              ODAK,
            )}
          >
            {acik ? (
              <X aria-hidden="true" className="size-[22px]" />
            ) : (
              <Menu aria-hidden="true" className="size-[22px]" />
            )}
          </button>
        </div>
      </nav>

      {acik ? (
        <div
          id="karsilama-mobil-menu"
          className="border-t border-kenar lg:hidden"
        >
          <div className={cn(KAPSAYICI, "flex flex-col py-3")}>
            {baglantilar("px-1 text-base", true)}
            <Link
              href={YOLLAR.kayit}
              className={cn(
                "mt-3 inline-flex h-12 items-center justify-center rounded-[10px] bg-ana px-5 font-semibold text-zemin hover:bg-ana/90",
                ODAK,
              )}
            >
              {MENU.kayit}
            </Link>
          </div>
        </div>
      ) : null}
    </header>
  );
}
