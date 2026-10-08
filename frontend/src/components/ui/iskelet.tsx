import { cn } from "@/lib/utils";

/**
 * Yükleniyor yer tutucuları (docs/design-language.md § Sayfa Düzeni): veri
 * gelmeden önce içeriğin yerini ve boyutunu gösterir, veri gelince sayfa
 * atlamaz. Ekran okuyucu "Yükleniyor…" duyar; hareket tercihi kapalıysa
 * titreşim durur.
 */

export function Iskelet({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "animate-pulse rounded-lg bg-kenar/60 motion-reduce:animate-none",
        className,
      )}
    />
  );
}

/** Bölüm içi liste: veri gelene kadar `satir` kadar kart. */
export function ListeIskeleti({
  satir = 2,
  className,
}: {
  satir?: number;
  className?: string;
}) {
  return (
    <div role="status" className={cn("flex flex-col gap-3", className)}>
      <span className="sr-only">Yükleniyor…</span>
      {Array.from({ length: satir }, (_, i) => (
        <Iskelet key={i} className="h-24 rounded-xl" />
      ))}
    </div>
  );
}

function BaslikIskeleti() {
  return (
    <div className="flex flex-col gap-3">
      <Iskelet className="h-8 w-2/5" />
      <Iskelet className="h-4 w-3/5" />
    </div>
  );
}

/** Bütün sayfa: başlık ve iki kart; geniş sayfada yan sütun da. */
export function SayfaIskeleti({ genis = false }: { genis?: boolean }) {
  if (genis) {
    return (
      <div
        role="status"
        className="grid items-start gap-8 lg:grid-cols-[19rem_minmax(0,1fr)]"
      >
        <span className="sr-only">Yükleniyor…</span>
        <div className="hidden flex-col gap-4 lg:flex">
          <Iskelet className="h-32 rounded-xl" />
          <Iskelet className="h-48 rounded-xl" />
        </div>
        <div className="flex flex-col gap-6">
          <BaslikIskeleti />
          <Iskelet className="h-44 rounded-xl" />
          <Iskelet className="h-44 rounded-xl" />
        </div>
      </div>
    );
  }
  return (
    <div role="status" className="flex flex-col gap-6">
      <span className="sr-only">Yükleniyor…</span>
      <BaslikIskeleti />
      <Iskelet className="h-44 rounded-xl" />
      <Iskelet className="h-44 rounded-xl" />
    </div>
  );
}
