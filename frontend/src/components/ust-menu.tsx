"use client";

/**
 * Üst menü, role göre (docs/faz-b-kimlik-ve-dongu.md § 7):
 *   Girişsiz: Giriş, Kayıt
 *   Genç:     Panelim, Yeni kart (Keşif), Bildirimler (rozet), Çıkış
 *   Kurum:    Panelim, Yeni ihtiyaç (Tanımlama), Bildirimler (rozet), Çıkış
 *   GİRVAK:   Panel, Çıkış
 *
 * Rozet /me'deki okunmamış sayısı; oturum sağlayıcısı onu sayfa değişiminde
 * ve 60 saniyede bir tazeliyor.
 */

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { cn } from "@/lib/utils";
import { useOturum } from "@/lib/oturum";
import { panelYolu } from "@/lib/yonlendirme";

type Baglanti = { yol: string; etiket: string; rozet?: number };

export function UstMenu() {
  const { oturum, cikisYap } = useOturum();
  const pathname = usePathname();
  const router = useRouter();

  let baglantilar: Baglanti[] = [];
  if (oturum.durum === "girissiz") {
    baglantilar = [
      { yol: "/giris", etiket: "Giriş" },
      { yol: "/kayit", etiket: "Kayıt" },
    ];
  } else if (oturum.durum === "girisli") {
    const { rol, okunmamis_bildirim } = oturum.hesap;
    const panel = {
      yol: panelYolu(rol),
      etiket: rol === "girvak" ? "Panel" : "Panelim",
    };
    const bildirim = {
      yol: "/bildirimler",
      etiket: "Bildirimler",
      rozet: okunmamis_bildirim,
    };
    if (rol === "genc") {
      baglantilar = [panel, { yol: "/kesif", etiket: "Yeni kart" }, bildirim];
    } else if (rol === "kurum") {
      baglantilar = [
        panel,
        { yol: "/tanimlama", etiket: "Yeni ihtiyaç" },
        bildirim,
      ];
    } else {
      baglantilar = [panel];
    }
  }

  return (
    <header className="border-b border-kenar bg-zemin">
      <nav
        aria-label="Ana menü"
        className="mx-auto flex w-full max-w-3xl flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3 sm:px-6"
      >
        <Link
          href="/"
          className="mr-auto font-heading text-lg font-semibold text-ana"
        >
          Zemin360
        </Link>

        {baglantilar.map((baglanti) => {
          const aktif =
            pathname === baglanti.yol ||
            pathname.startsWith(`${baglanti.yol}/`);
          return (
            <Link
              key={baglanti.yol}
              href={baglanti.yol}
              aria-current={aktif ? "page" : undefined}
              className={cn(
                "inline-flex items-center gap-1.5 text-sm underline-offset-4 hover:underline",
                aktif ? "font-medium text-ana" : "text-muted-foreground",
              )}
            >
              {baglanti.etiket}
              {baglanti.rozet ? (
                <span
                  className="rounded-full bg-vurgu px-1.5 font-mono text-[0.7rem] leading-5 text-white"
                  aria-label={`${baglanti.rozet} okunmamış`}
                >
                  {baglanti.rozet > 99 ? "99+" : baglanti.rozet}
                </span>
              ) : null}
            </Link>
          );
        })}

        {oturum.durum === "girisli" ? (
          <button
            type="button"
            onClick={() => {
              cikisYap();
              router.push("/");
            }}
            className="text-sm text-muted-foreground underline-offset-4 hover:underline"
          >
            Çıkış
          </button>
        ) : null}
      </nav>
    </header>
  );
}
