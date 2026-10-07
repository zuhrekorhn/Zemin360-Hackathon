import Link from "next/link";

import { BackendDurumu } from "@/components/backend-durumu";
import { DemoKarti } from "@/components/karsilama/demo-karti";
import {
  HeroKapilari,
  KapanisKapilari,
} from "@/components/karsilama/kapilar";
import { NasilCalisir } from "@/components/karsilama/nasil-calisir";
import { NedenUygunOrnegi } from "@/components/karsilama/neden-uygun";
import {
  KAPSAYICI,
  ODAK,
  UST_ETIKET,
} from "@/components/karsilama/ortak";
import {
  ALTBILGI,
  GUVEN,
  HERO,
  KAPANIS,
  SEFFAF,
  SORUN,
  SUREC,
} from "@/content/landing";
import { cn } from "@/lib/utils";

// Karşılama sayfası. Metinler content/landing.ts'te; renk ve font mevcut paletten
// (docs/design-language.md). Backend kapalıyken de eksiksiz görünür.

/** Geliştirme göstergesi yalnızca açıkça istenirse. */
const GELISTIRME_DURUMU = process.env.NEXT_PUBLIC_SHOW_DEV_STATUS === "true";

const H2 =
  "font-heading text-[28px] leading-[1.1] font-semibold text-ana lg:text-[44px]";

const METIN_BAGLANTISI = cn(
  "rounded-sm font-semibold text-ana underline underline-offset-4 hover:text-baglanti",
  ODAK,
);

export default function AnaSayfa() {
  return (
    <>
      <main className="flex w-full flex-1 flex-col">
        {/* 3.2 Hero */}
        <section className="pt-9 pb-10 sm:pt-16 sm:pb-20 lg:pt-24 lg:pb-28">
          <div
            className={cn(
              KAPSAYICI,
              "grid items-center gap-8 lg:grid-cols-2 lg:gap-[72px]",
            )}
          >
            <div className="flex flex-col gap-5 lg:gap-[26px]">
              <p className="self-start rounded-full bg-baglanti/12 px-3 py-1.5 text-[13px] font-semibold text-ana sm:px-3.5 sm:py-2 sm:text-sm">
                {HERO.etiket}
              </p>
              <h1 className="font-heading text-[40px] leading-[1.06] font-semibold tracking-[-0.015em] text-balance text-ana lg:text-[64px] lg:leading-[1.04] lg:tracking-[-0.02em]">
                {HERO.baslik}
              </h1>
              <p className="max-w-[540px] text-[17px] leading-[1.55] text-pretty text-muted-foreground lg:text-xl">
                {HERO.metin}
              </p>
              <div className="mt-1 max-w-[560px] lg:mt-1.5">
                <HeroKapilari />
              </div>
            </div>

            <DemoKarti />
          </div>
        </section>

        {/* 3.3 Sorun bandı */}
        <section
          aria-labelledby="sorun-baslik"
          className="bg-metin py-10 text-zemin sm:py-16 lg:py-[88px]"
        >
          <div className={cn(KAPSAYICI, "flex flex-col gap-6 lg:gap-12")}>
            <h2
              id="sorun-baslik"
              className="max-w-[820px] font-heading text-[28px] leading-[1.2] font-medium text-balance lg:text-[40px] lg:leading-[1.15]"
            >
              {SORUN.baslik}
            </h2>
            <ul className="grid gap-6 md:grid-cols-3 lg:gap-10">
              {SORUN.maddeler.map((madde) => (
                <li
                  key={madde.baslik}
                  className="flex flex-col gap-1.5 border-t border-zemin/20 pt-4 lg:gap-2.5 lg:pt-5"
                >
                  <h3 className="text-[17px] font-semibold lg:text-[19px]">
                    {madde.baslik}
                  </h3>
                  <p className="text-[15px] leading-relaxed text-zemin/75 lg:text-base">
                    {madde.metin}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* 3.4 Nasıl çalışır */}
        <NasilCalisir />

        {/* 3.5 Şeffaf eşleşme */}
        <section
          aria-labelledby="seffaf-baslik"
          className="pb-16 sm:pb-24 lg:pb-28"
        >
          <div
            className={cn(
              KAPSAYICI,
              "grid items-center gap-8 lg:grid-cols-2 lg:gap-[72px]",
            )}
          >
            <div className="flex flex-col gap-4 lg:gap-5">
              <p className={UST_ETIKET}>{SEFFAF.ustEtiket}</p>
              <h2 id="seffaf-baslik" className={H2}>
                {SEFFAF.baslik}
              </h2>
              <p className="text-[17px] leading-relaxed text-pretty text-muted-foreground lg:text-lg">
                {SEFFAF.metin}
              </p>
              <a
                href={SEFFAF.baglanti.hedef}
                className={cn(
                  METIN_BAGLANTISI,
                  "inline-flex min-h-11 items-center self-start",
                )}
              >
                {SEFFAF.baglanti.etiket}
              </a>
            </div>
            <NedenUygunOrnegi />
          </div>
        </section>

        {/* 3.6 Süreç */}
        <section
          id="surec"
          aria-labelledby="surec-baslik"
          className="scroll-mt-16 lg:scroll-mt-[77px] bg-muted py-16 sm:py-24 lg:py-[104px]"
        >
          <div className={cn(KAPSAYICI, "flex flex-col gap-8 lg:gap-12")}>
            <div className="flex max-w-[780px] flex-col gap-3.5">
              <p className={UST_ETIKET}>{SUREC.ustEtiket}</p>
              <h2 id="surec-baslik" className={cn(H2, "text-balance")}>
                {SUREC.baslik}
              </h2>
              <p className="text-[17px] leading-relaxed text-muted-foreground lg:text-lg">
                {SUREC.metin}
              </p>
            </div>

            <ol className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6">
              {SUREC.kartlar.map((kart) => (
                <li
                  key={kart.no}
                  className="flex flex-col gap-3 rounded-2xl bg-card px-[18px] py-[22px] xl:min-h-[260px]"
                >
                  <span className="font-mono text-sm text-muted-foreground">
                    {kart.no}
                  </span>
                  <p className="text-[15px] leading-snug text-muted-foreground italic">
                    “{kart.soru}”
                  </p>
                  <span aria-hidden="true" className="h-px bg-kenar" />
                  <h3 className="font-heading text-[19px] leading-tight font-semibold text-ana">
                    {kart.baslik}
                  </h3>
                  <p className="text-sm leading-normal text-muted-foreground">
                    {kart.metin}
                  </p>
                </li>
              ))}
            </ol>

            <p className="flex items-start gap-3.5 text-base text-metin">
              <svg
                aria-hidden="true"
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="mt-px shrink-0 text-vurgu"
              >
                <path d="M21 12a9 9 0 1 1-3-6.7" />
                <path d="M21 4v5h-5" />
              </svg>
              <span>{SUREC.dongu}</span>
            </p>
          </div>
        </section>

        {/* 3.7 Güven */}
        <section className="py-16 sm:py-24 lg:py-[104px]">
          <div className={cn(KAPSAYICI, "grid gap-8 md:grid-cols-3 lg:gap-10")}>
            {GUVEN.maddeler.map((madde) => (
              <div key={madde.baslik} className="flex flex-col gap-2.5">
                <h2 className="text-lg font-semibold text-metin lg:text-xl">
                  {madde.baslik}
                </h2>
                <p className="leading-relaxed text-muted-foreground">
                  {madde.metin}
                  {madde.baglanti ? (
                    <>
                      {" "}
                      <Link
                        href={madde.baglanti.hedef}
                        className={METIN_BAGLANTISI}
                      >
                        {madde.baglanti.etiket}
                      </Link>
                    </>
                  ) : null}
                </p>
              </div>
            ))}

            <div className="flex flex-col gap-5 border-t border-kenar pt-8 md:col-span-3 md:mt-6 md:flex-row md:items-center md:gap-7">
              <p className="text-[15px] text-muted-foreground">
                {GUVEN.program}
              </p>
              {/* Logo yeri: gerçek logolar eklenene kadar boş kutu. */}
              <div aria-hidden="true" className="flex shrink-0 gap-4 md:gap-7">
                <span className="h-11 w-[120px] rounded-lg border border-dashed border-muted-foreground/40" />
                <span className="h-11 w-[120px] rounded-lg border border-dashed border-muted-foreground/40" />
              </div>
            </div>
          </div>
        </section>

        {/* 3.8 Kapanış */}
        <section aria-labelledby="kapanis-baslik" className={KAPSAYICI}>
          <div className="grid items-center gap-8 rounded-[28px] bg-ana p-8 sm:p-12 lg:grid-cols-2 lg:gap-12 lg:p-[72px]">
            <h2
              id="kapanis-baslik"
              className="font-heading text-[28px] leading-[1.15] font-medium text-balance text-zemin lg:text-[44px] lg:leading-[1.12]"
            >
              {KAPANIS.baslik}
            </h2>
            <KapanisKapilari />
          </div>
        </section>
      </main>

      {/* 3.9 Altbilgi */}
      <footer
        className={cn(
          KAPSAYICI,
          "flex flex-col gap-6 pt-14 pb-12 text-sm text-muted-foreground md:flex-row md:items-end md:justify-between",
        )}
      >
        <div className="flex flex-col gap-2">
          <p className="font-heading text-xl font-semibold text-ana">
            {ALTBILGI.logo}
          </p>
          <p>{ALTBILGI.slogan}</p>
          {GELISTIRME_DURUMU ? <BackendDurumu /> : null}
        </div>
        <ul className="flex gap-6 md:gap-7">
          {ALTBILGI.baglantilar.map((baglanti) => (
            <li key={baglanti.etiket}>
              <Link
                href={baglanti.hedef}
                className={cn(
                  "inline-flex min-h-11 items-center rounded-sm text-muted-foreground hover:text-ana",
                  ODAK,
                )}
              >
                {baglanti.etiket}
              </Link>
            </li>
          ))}
        </ul>
      </footer>
    </>
  );
}
