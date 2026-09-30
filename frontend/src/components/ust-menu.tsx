"use client";

/**
 * Üst menü, role göre (docs/faz-b-kimlik-ve-dongu.md § 7):
 *   Girişsiz: Giriş yap, Kayıt ol (/ sayfasında karşılama menüsü)
 *   Genç:     Panelim, Yeni kart (Keşif), Profilim, Bildirimler (rozet), Çıkış
 *   Kurum:    Panelim, Yeni ihtiyaç, Firma kartı, Firma profili, Bildirimler, Çıkış
 *   GİRVAK:   Panel, Çıkış
 *
 * İskelet MenuKabugu'nda (karşılama menüsüyle ortak). Mobilde bağlantılar
 * katlanır menüde; bildirim zili ve rozeti katlanmadan görünür kalır.
 *
 * Rozet /me'deki okunmamış sayısı; oturum sağlayıcısı onu sayfa değişiminde
 * ve 60 saniyede bir tazeliyor.
 */

import { Bell } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { KarsilamaMenusu } from "@/components/karsilama/menu";
import { MENU_ODAK, MenuKabugu } from "@/components/menu-kabugu";
import { cn } from "@/lib/utils";
import { useOturum } from "@/lib/oturum";
import { panelYolu } from "@/lib/yonlendirme";

type Baglanti = { yol: string; etiket: string; rozet?: number };

function Rozet({ sayi }: { sayi: number }) {
  return (
    <span
      className="rounded-full bg-vurgu px-1.5 font-mono text-[0.7rem] leading-5 text-metin"
      aria-hidden="true"
    >
      {sayi > 99 ? "99+" : sayi}
    </span>
  );
}

export function UstMenu() {
  const { oturum, cikisYap } = useOturum();
  const pathname = usePathname();
  const router = useRouter();

  // Karşılama sayfası kendi menüsünü taşır (brief § 3.1); girişli kullanıcı
  // / sayfasında da her zamanki menüyü görür.
  if (pathname === "/" && oturum.durum !== "girisli") {
    return <KarsilamaMenusu />;
  }

  if (oturum.durum !== "girisli") {
    // Girişsiz (ya da oturum henüz bilinmiyor): iki kısa bağlantı her
    // ekrana sığar, katlanır menü gerekmez.
    return (
      <MenuKabugu
        sag={
          oturum.durum === "girissiz" ? (
            <>
              <Link
                href="/giris"
                className={cn(
                  "inline-flex h-11 items-center rounded-lg px-3 font-medium text-metin hover:text-ana",
                  MENU_ODAK,
                )}
              >
                Giriş yap
              </Link>
              <Link
                href="/kayit"
                className={cn(
                  "inline-flex h-11 items-center rounded-[10px] bg-ana px-4 font-semibold text-zemin hover:bg-ana/90 lg:px-5",
                  MENU_ODAK,
                )}
              >
                Kayıt ol
              </Link>
            </>
          ) : null
        }
      />
    );
  }

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
  let baglantilar: Baglanti[] = [panel];
  if (rol === "genc") {
    baglantilar = [
      panel,
      { yol: "/kesif", etiket: "Yeni kart" },
      { yol: "/profil", etiket: "Profilim" },
      bildirim,
    ];
  } else if (rol === "kurum") {
    baglantilar = [
      panel,
      { yol: "/tanimlama", etiket: "Yeni ihtiyaç" },
      { yol: "/kurum/kart", etiket: "Firma kartı" },
      { yol: "/kurum/profil", etiket: "Firma profili" },
      bildirim,
    ];
  }
  const zil = rol !== "girvak";

  const aktifMi = (yol: string) =>
    pathname === yol || pathname.startsWith(`${yol}/`);

  const cikis = () => {
    cikisYap();
    router.push("/");
  };

  const baglantiListesi = (mobil: boolean, kapat?: () => void) =>
    baglantilar.map((baglanti) => {
      const aktif = aktifMi(baglanti.yol);
      return (
        <Link
          key={baglanti.yol}
          href={baglanti.yol}
          onClick={kapat}
          aria-current={aktif ? "page" : undefined}
          className={cn(
            "inline-flex min-h-11 items-center gap-1.5 rounded-sm hover:text-ana",
            mobil ? "px-1 text-base" : "text-[15px]",
            aktif ? "font-semibold text-ana" : "text-muted-foreground",
            MENU_ODAK,
          )}
        >
          {/* Alt çizgi yalnızca etikette; rozetin altına uzanmasın. */}
          <span
            className={cn(
              aktif &&
                "underline decoration-vurgu decoration-2 underline-offset-8",
            )}
          >
            {baglanti.etiket}
          </span>
          {baglanti.rozet ? (
            <>
              <Rozet sayi={baglanti.rozet} />
              <span className="sr-only">, {baglanti.rozet} okunmamış</span>
            </>
          ) : null}
        </Link>
      );
    });

  const cikisSinifi = cn(
    "inline-flex min-h-11 items-center rounded-sm text-muted-foreground hover:text-ana",
    MENU_ODAK,
  );

  return (
    <MenuKabugu
      masaustu={baglantiListesi(false)}
      sag={
        <>
          {zil ? (
            <Link
              href="/bildirimler"
              aria-current={aktifMi("/bildirimler") ? "page" : undefined}
              className={cn(
                "relative inline-flex size-11 items-center justify-center rounded-lg text-metin lg:hidden",
                MENU_ODAK,
              )}
            >
              <Bell aria-hidden="true" className="size-5" />
              <span className="sr-only">
                Bildirimler
                {okunmamis_bildirim
                  ? `, ${okunmamis_bildirim} okunmamış`
                  : ""}
              </span>
              {okunmamis_bildirim ? (
                <span className="absolute top-1 right-0.5">
                  <Rozet sayi={okunmamis_bildirim} />
                </span>
              ) : null}
            </Link>
          ) : null}
          <button
            type="button"
            onClick={cikis}
            className={cn(cikisSinifi, "hidden text-[15px] lg:inline-flex")}
          >
            Çıkış
          </button>
        </>
      }
      mobil={(kapat) => (
        <>
          {baglantiListesi(true, kapat)}
          <button
            type="button"
            onClick={() => {
              kapat();
              cikis();
            }}
            className={cn(
              cikisSinifi,
              "mt-2 border-t border-kenar px-1 pt-2 text-base",
            )}
          >
            Çıkış
          </button>
        </>
      )}
    />
  );
}
