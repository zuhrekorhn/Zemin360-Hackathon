"use client";

/**
 * Üst menünün iskeleti — karşılama menüsü ve uygulama menüsü aynı kabuğu
 * giyer; girişten önce ve sonra marka aynı yerde, aynı yükseklikte durur
 * (docs/design-language.md § Sayfa düzeni).
 *
 * Yapışkan: sayfa kaydırılınca menü kaybolmaz. Geniş ekranda bağlantılar
 * satırda; lg altında katlanır menüye girer (açılınca Escape kapatır).
 * `sag` her ekranda görünür kalır (ör. giriş düğmesi, bildirim zili).
 */

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { useRef, useState, type ReactNode } from "react";

import { GENIS_KAPSAYICI } from "@/components/sayfa";
import { cn } from "@/lib/utils";

/** Açık zeminde görünür odak halkası; menüdeki her tıklanabilir öğe için. */
export const MENU_ODAK =
  "outline-none focus-visible:ring-3 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background";

export function MenuKabugu({
  masaustu,
  ortala = false,
  sag,
  mobil,
}: {
  /** Geniş ekranda satırdaki bağlantılar. */
  masaustu?: ReactNode;
  /** Bağlantılar ortada mı (karşılama), logonun yanında mı (uygulama). */
  ortala?: boolean;
  /** Her ekranda görünen sağ taraf. */
  sag?: ReactNode;
  /** Katlanır menünün içeriği; verilmezse menü düğmesi çıkmaz. */
  mobil?: (kapat: () => void) => ReactNode;
}) {
  const [acik, setAcik] = useState(false);
  const dugme = useRef<HTMLButtonElement>(null);
  const kapat = () => setAcik(false);

  return (
    // Escape menünün herhangi bir yerinden (düğme dahil) katlanır menüyü kapatır.
    <header
      onKeyDown={(olay) => {
        if (olay.key === "Escape" && acik) {
          kapat();
          dugme.current?.focus();
        }
      }}
      className="sticky top-0 z-40 border-b border-kenar bg-zemin print:hidden"
    >
      <nav
        aria-label="Ana menü"
        className={cn(
          GENIS_KAPSAYICI,
          "flex h-16 items-center gap-4 lg:h-[76px]",
        )}
      >
        <Link
          href="/"
          className={cn(
            "rounded-sm font-heading text-[21px] font-semibold text-ana lg:text-2xl",
            MENU_ODAK,
          )}
        >
          Zemin360
        </Link>

        {masaustu ? (
          <div
            className={cn(
              "hidden items-center lg:flex",
              ortala ? "mx-auto gap-9" : "ml-6 gap-7",
            )}
          >
            {masaustu}
          </div>
        ) : null}

        <div className="ml-auto flex items-center gap-1 lg:gap-3">
          {sag}
          {mobil ? (
            <button
              ref={dugme}
              type="button"
              aria-expanded={acik}
              aria-controls="mobil-menu"
              aria-label={acik ? "Menüyü kapat" : "Menüyü aç"}
              onClick={() => setAcik((onceki) => !onceki)}
              className={cn(
                "inline-flex size-11 items-center justify-center rounded-lg text-metin lg:hidden",
                MENU_ODAK,
              )}
            >
              {acik ? (
                <X aria-hidden="true" className="size-[22px]" />
              ) : (
                <Menu aria-hidden="true" className="size-[22px]" />
              )}
            </button>
          ) : null}
        </div>
      </nav>

      {mobil && acik ? (
        <div id="mobil-menu" className="border-t border-kenar lg:hidden">
          <div className={cn(GENIS_KAPSAYICI, "flex flex-col py-3")}>
            {mobil(kapat)}
          </div>
        </div>
      ) : null}
    </header>
  );
}
