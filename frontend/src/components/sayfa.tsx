/**
 * Sayfa kabuğu — uygulamadaki her iç sayfanın düzeni tek yerde
 * (docs/design-language.md § Sayfa düzeni).
 *
 *   <Sayfa genislik="form">
 *     <SayfaBasligi baslik="Profilim" aciklama="…" />
 *     …bölümler…
 *   </Sayfa>
 *
 * Genişlik içeriğin türüne göre seçilir, sayfaya göre değil: okunan ve
 * listelenen içerik "icerik", form "form", tek alanlı kısa form "dar".
 * Yükleniyor ve hata durumları da aynı kabukla çizilir (SayfaDurumu), yoksa
 * veri gelince içerik yana ya da aşağı kayar.
 */

import type { ReactNode } from "react";

import { HataKutusu } from "@/components/sohbet";
import type { Hata } from "@/lib/hata";
import { cn } from "@/lib/utils";

export type Genislik = "genis" | "icerik" | "form" | "dar";

const GENISLIKLER: Record<Genislik, string> = {
  genis: "max-w-5xl", // 1024px — iki sütunlu ana sayfa: akış + yan sütun
  icerik: "max-w-2xl", // 672px — okunabilir satır uzunluğu, panel bir "belge"
  form: "max-w-xl", // 576px — tek sütunlu form
  dar: "max-w-md", // 448px — giriş gibi birkaç alanlı form
};

/** Kenar payı: karşılama sayfası ve menüyle aynı (mobilde 20px). */
export const KENAR_PAYI = "px-5 sm:px-8";

/** Menü ve karşılama sayfası: 1200px'lik geniş kapsayıcı. */
export const GENIS_KAPSAYICI = cn(
  "mx-auto w-full max-w-[1200px] lg:px-10",
  KENAR_PAYI,
);

export function Sayfa({
  genislik = "icerik",
  children,
}: {
  genislik?: Genislik;
  children: ReactNode;
}) {
  return (
    <main
      className={cn(
        "mx-auto flex w-full flex-1 flex-col gap-8 py-10 sm:py-16",
        KENAR_PAYI,
        GENISLIKLER[genislik],
      )}
    >
      {children}
    </main>
  );
}

/**
 * Sayfanın tek h1'i. `etiket` başlığın yanında (ör. iş birliğinin durumu),
 * `eylem` sağda (ör. "Hepsini okundu say"), `children` açıklamanın altındaki
 * ek satırlar (ör. ihtiyacın problem tanımı).
 */
export function SayfaBasligi({
  baslik,
  aciklama,
  etiket,
  eylem,
  children,
}: {
  baslik: ReactNode;
  aciklama?: ReactNode;
  etiket?: ReactNode;
  eylem?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex min-w-0 flex-1 basis-80 flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-heading text-2xl font-semibold text-balance text-ana sm:text-3xl">
            {baslik}
          </h1>
          {etiket}
        </div>
        {aciklama ? (
          <p className="text-sm text-pretty text-muted-foreground">
            {aciklama}
          </p>
        ) : null}
        {children}
      </div>
      {eylem ? <div className="shrink-0">{eylem}</div> : null}
    </header>
  );
}

/** Veri gelmeden önceki sayfa: aynı kabuk, aynı genişlik. */
export function SayfaDurumu({
  genislik,
  hata,
  tekrarDene,
}: {
  genislik?: Genislik;
  hata?: Hata | null;
  tekrarDene?: () => void;
}) {
  return (
    <Sayfa genislik={genislik}>
      {hata ? (
        <HataKutusu hata={hata} tekrarDene={tekrarDene} />
      ) : (
        <p className="text-sm text-muted-foreground" role="status">
          Yükleniyor…
        </p>
      )}
    </Sayfa>
  );
}
