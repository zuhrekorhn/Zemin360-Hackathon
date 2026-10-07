"use client";

import { X } from "lucide-react";
import { useEffect, useId, useRef } from "react";

/**
 * Sağdan açılan panel: bir öğenin bütün işlerini sayfadan ayırmadan tek yerde
 * toplar (kart sayfasında "Güçlendir", "Kartı düzenle"). Arka plan karartılır;
 * Escape ve dışarı tıklama kapatır, açıkken sayfa kaymaz, odak panele gider.
 * Mobilde tam genişlik.
 */
export function YanPanel({
  acik,
  onKapat,
  ust,
  baslik,
  alt,
  children,
  etek,
}: {
  acik: boolean;
  onKapat: () => void;
  /** Başlığın üstündeki küçük satır: "Çalışmayı güçlendir". */
  ust?: string;
  baslik: string;
  /** Başlığın altındaki durum: "3 adım kaldı · Referans tamam". */
  alt?: string;
  children: React.ReactNode;
  etek?: React.ReactNode;
}) {
  const kimlik = useId();
  const panel = useRef<HTMLDivElement>(null);
  // Kapatma fonksiyonu her çizimde yenilense de efekt yeniden kurulmasın.
  const kapat = useRef(onKapat);
  useEffect(() => {
    kapat.current = onKapat;
  }, [onKapat]);

  useEffect(() => {
    if (!acik) return;
    const onceki = document.activeElement as HTMLElement | null;
    const tasma = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panel.current?.focus();
    function tus(olay: KeyboardEvent) {
      if (olay.key === "Escape") kapat.current();
    }
    document.addEventListener("keydown", tus);
    return () => {
      document.removeEventListener("keydown", tus);
      document.body.style.overflow = tasma;
      onceki?.focus();
    };
  }, [acik]);

  if (!acik) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div
        aria-hidden="true"
        onClick={onKapat}
        className="absolute inset-0 bg-metin/35 motion-safe:animate-in motion-safe:fade-in-0"
      />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={kimlik}
        tabIndex={-1}
        className="absolute inset-y-0 right-0 flex w-full max-w-[460px] flex-col bg-zemin shadow-[-12px_0_40px_-16px_rgb(22_33_27/0.35)] outline-none motion-safe:animate-in motion-safe:slide-in-from-right-8 motion-safe:fade-in-0"
      >
        <header className="flex items-start justify-between gap-4 border-b border-kenar bg-card px-6 py-5">
          <div className="flex min-w-0 flex-col gap-1">
            {ust ? (
              <p className="text-xs font-medium text-muted-foreground">{ust}</p>
            ) : null}
            <h2
              id={kimlik}
              className="font-heading text-xl leading-snug font-semibold text-balance text-ana"
            >
              {baslik}
            </h2>
            {alt ? (
              <p className="text-sm text-muted-foreground">{alt}</p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onKapat}
            aria-label="Paneli kapat"
            className="inline-flex size-9 shrink-0 items-center justify-center rounded-lg border border-kenar text-metin outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <X aria-hidden="true" className="size-4" />
          </button>
        </header>
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-6 py-5">
          {children}
        </div>
        {etek ? (
          <footer className="flex items-center justify-between gap-3 border-t border-kenar bg-card px-6 py-4">
            {etek}
          </footer>
        ) : null}
      </div>
    </div>
  );
}
