"use client";

/**
 * Üst menü, role göre (docs/kimlik-ve-dongu.md § 7, docs/design-language.md § Sayfa düzeni):
 *   Girişsiz: Giriş yap, Kayıt ol (/ sayfasında karşılama menüsü)
 *   Genç:     Fırsatlar, Kartım (yoksa Keşif), İş birliklerim · zil · hesap menüsü (Hesabım, Çıkış)
 *   Kurum:    Panelim, Yeni ihtiyaç, Firma kartı · zil · hesap menüsü (Firma profili, Çıkış)
 *   GİRVAK:   Panel · hesap menüsü (Çıkış)
 *
 * Bağlantılar yalnızca sayfa; hesapla ilgili olan (ayarlar, çıkış) adın
 * altındaki menüde. Zil ve okunmamış sayısı her ekranda görünür. İskelet
 * MenuKabugu'nda (karşılama menüsüyle ortak); mobilde bağlantılar ve hesap
 * menüsünün öğeleri katlanır menüde.
 *
 * Rozet /me'deki okunmamış sayısı; oturum sağlayıcısı onu sayfa değişiminde
 * ve 60 saniyede bir tazeliyor.
 */

import { Bell, ChevronDown } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { KarsilamaMenusu } from "@/components/karsilama/menu";
import { basHarfler } from "@/components/kart-yan-sutunu";
import { MENU_ODAK, MenuKabugu } from "@/components/menu-kabugu";
import { adGosterimi } from "@/lib/ad";
import type { MeYaniti } from "@/lib/api";
import { menuBaglantilari, type MenuBaglantisi } from "@/lib/menu";
import { cn } from "@/lib/utils";
import { useOturum } from "@/lib/oturum";

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

/** Adın baş harfleri (kart sayfasıyla aynı); ad yoksa e-postanın ilk harfi. */
function basHarf(hesap: MeYaniti): string {
  return hesap.ad
    ? basHarfler(hesap.ad)
    : hesap.email.charAt(0).toLocaleUpperCase("tr");
}

function HesapMenusu({
  hesap,
  ayar,
  onCikis,
}: {
  hesap: MeYaniti;
  ayar: MenuBaglantisi | null;
  onCikis: () => void;
}) {
  const [acik, setAcik] = useState(false);
  const kutu = useRef<HTMLDivElement>(null);
  const dugme = useRef<HTMLButtonElement>(null);

  // Dışarı tıklayınca ya da Escape'le kapanır.
  useEffect(() => {
    if (!acik) return;
    function disari(olay: MouseEvent) {
      if (!kutu.current?.contains(olay.target as Node)) setAcik(false);
    }
    function tus(olay: KeyboardEvent) {
      if (olay.key === "Escape") {
        setAcik(false);
        dugme.current?.focus();
      }
    }
    document.addEventListener("mousedown", disari);
    document.addEventListener("keydown", tus);
    return () => {
      document.removeEventListener("mousedown", disari);
      document.removeEventListener("keydown", tus);
    };
  }, [acik]);

  const ad = hesap.ad ? adGosterimi(hesap.ad) : hesap.email;
  const ogeSinifi = cn(
    "flex min-h-10 w-full items-center rounded-md px-3 text-left text-sm text-metin hover:bg-muted",
    MENU_ODAK,
  );

  return (
    <div ref={kutu} className="relative hidden lg:block">
      <button
        ref={dugme}
        type="button"
        aria-expanded={acik}
        aria-controls="hesap-menusu"
        onClick={() => setAcik((onceki) => !onceki)}
        className={cn(
          "inline-flex h-11 items-center gap-2 rounded-lg pr-1.5 pl-1 text-[15px] text-metin hover:bg-muted",
          MENU_ODAK,
        )}
      >
        <span
          aria-hidden="true"
          className="flex size-8 items-center justify-center rounded-full bg-ana font-heading text-xs font-semibold text-zemin"
        >
          {basHarf(hesap)}
        </span>
        <span className="max-w-40 truncate">{ad}</span>
        <ChevronDown
          aria-hidden="true"
          className={cn("size-4 transition-transform", acik && "rotate-180")}
        />
      </button>
      {acik ? (
        <div
          id="hesap-menusu"
          className="absolute top-full right-0 z-50 mt-2 flex w-60 flex-col gap-0.5 rounded-lg border border-kenar bg-card p-1.5 shadow-[0_8px_24px_-12px_rgb(22_33_27/0.25)]"
        >
          <div className="px-3 pt-1.5 pb-2">
            <p className="truncate text-sm font-medium text-ana">{ad}</p>
            <p className="truncate text-xs text-muted-foreground">
              {hesap.email}
            </p>
          </div>
          <div className="border-t border-kenar pt-1">
            {ayar ? (
              <Link
                href={ayar.yol}
                onClick={() => setAcik(false)}
                className={ogeSinifi}
              >
                {ayar.etiket}
              </Link>
            ) : null}
            <button
              type="button"
              onClick={() => {
                setAcik(false);
                onCikis();
              }}
              className={ogeSinifi}
            >
              Çıkış
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function UstMenu() {
  const { oturum, cikisYap } = useOturum();
  const pathname = usePathname();
  const router = useRouter();

  // Karşılama sayfası kendi menüsünü taşır; girişli kullanıcı
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

  const hesap = oturum.hesap;
  const { okunmamis_bildirim } = hesap;
  const { baglantilar, ayar } = menuBaglantilari(hesap);
  const zil = hesap.rol !== "girvak";

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
          <span
            className={cn(
              aktif &&
                "underline decoration-vurgu decoration-2 underline-offset-8",
            )}
          >
            {baglanti.etiket}
          </span>
        </Link>
      );
    });

  const mobilOgeSinifi = cn(
    "inline-flex min-h-11 items-center rounded-sm px-1 text-base text-muted-foreground hover:text-ana",
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
                "relative inline-flex size-11 items-center justify-center rounded-lg text-metin hover:bg-muted",
                aktifMi("/bildirimler") && "bg-muted text-ana",
                MENU_ODAK,
              )}
            >
              <Bell aria-hidden="true" className="size-5" />
              <span className="sr-only">
                Bildirimler
                {okunmamis_bildirim ? `, ${okunmamis_bildirim} okunmamış` : ""}
              </span>
              {okunmamis_bildirim ? (
                <span className="absolute top-1 right-0.5">
                  <Rozet sayi={okunmamis_bildirim} />
                </span>
              ) : null}
            </Link>
          ) : null}
          <HesapMenusu hesap={hesap} ayar={ayar} onCikis={cikis} />
        </>
      }
      mobil={(kapat) => (
        <>
          {baglantiListesi(true, kapat)}
          <div className="mt-2 flex flex-col border-t border-kenar pt-2">
            {ayar ? (
              <Link href={ayar.yol} onClick={kapat} className={mobilOgeSinifi}>
                {ayar.etiket}
              </Link>
            ) : null}
            <button
              type="button"
              onClick={() => {
                kapat();
                cikis();
              }}
              className={cn(mobilOgeSinifi, "text-left")}
            >
              Çıkış
            </button>
          </div>
        </>
      )}
    />
  );
}
