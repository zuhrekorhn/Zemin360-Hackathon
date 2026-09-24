"use client";

import { Button } from "@/components/ui/button";

/**
 * Keşif ve Tanımlama sohbetlerinin paylaştığı iki görsel parça.
 *
 * Görsel dil (docs/design-language.md): balonlar yuvarlak/sıcak, hata kutusu
 * hairline çizgili. Sohbet akışının mantığı (durum, istekler) paylaşılmıyor —
 * her ajanın kendi sayfasında duruyor.
 */

export type Mesaj = { kim: "ajan" | "kullanici"; metin: string };

export type SohbetHatasi = { metin: string; kota: boolean };

export function Sohbet({
  ajanAdi,
  mesajlar,
  bekleniyor,
  sonMesajRef,
}: {
  ajanAdi: string;
  mesajlar: Mesaj[];
  bekleniyor: boolean;
  sonMesajRef: React.RefObject<HTMLDivElement | null>;
}) {
  return (
    <section
      aria-label="Sohbet"
      aria-live="polite"
      className="flex flex-col gap-3 rounded-[1.75rem] bg-muted p-4 sm:p-6"
    >
      {mesajlar.map((mesaj, sira) => (
        <p
          key={`${mesaj.kim}-${sira}`}
          className={
            mesaj.kim === "ajan"
              ? "max-w-[85%] rounded-3xl rounded-bl-lg bg-card px-4 py-3 text-sm text-pretty break-words ring-1 ring-kenar"
              : "ml-auto max-w-[85%] rounded-3xl rounded-br-lg bg-ana px-4 py-3 text-sm text-pretty break-words text-zemin"
          }
        >
          {mesaj.kim === "ajan" ? (
            <span className="mb-1 block font-medium text-baglanti">
              {ajanAdi}
            </span>
          ) : null}
          {mesaj.metin}
        </p>
      ))}

      {bekleniyor ? (
        <p className="flex max-w-[85%] items-center gap-2 rounded-3xl rounded-bl-lg bg-card px-4 py-3 text-sm text-muted-foreground ring-1 ring-kenar">
          <span
            aria-hidden="true"
            className="size-2 rounded-full bg-baglanti motion-safe:animate-pulse"
          />
          Ajan düşünüyor…
        </p>
      ) : null}

      <div ref={sonMesajRef} />
    </section>
  );
}

export function HataKutusu({
  hata,
  tekrarDene,
}: {
  hata: SohbetHatasi;
  tekrarDene: () => void;
}) {
  return (
    <div
      role="status"
      className="flex flex-col gap-3 rounded-sm border border-kenar bg-card px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="text-sm text-pretty">{hata.metin}</p>
      <Button
        type="button"
        variant="outline"
        size="lg"
        onClick={tekrarDene}
        className="w-fit shrink-0"
      >
        Tekrar dene
      </Button>
    </div>
  );
}

/** Sohbet giriş alanı — Enter gönderir, Shift+Enter satır atlar. */
export function CevapAlani({
  girdi,
  setGirdi,
  bekleniyor,
  gonder,
}: {
  girdi: string;
  setGirdi: (deger: string) => void;
  bekleniyor: boolean;
  gonder: () => void;
}) {
  return (
    <form
      onSubmit={(olay) => {
        olay.preventDefault();
        gonder();
      }}
      className="flex flex-col gap-3"
    >
      <label htmlFor="cevap" className="sr-only">
        Cevabın
      </label>
      <textarea
        id="cevap"
        value={girdi}
        onChange={(olay) => setGirdi(olay.target.value)}
        onKeyDown={(olay) => {
          if (olay.key === "Enter" && !olay.shiftKey) {
            olay.preventDefault();
            gonder();
          }
        }}
        rows={3}
        disabled={bekleniyor}
        placeholder="Yazmaya başla…"
        className="w-full resize-y rounded-2xl border border-kenar bg-card px-4 py-3 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30 disabled:opacity-60"
      />
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-muted-foreground">
          Enter gönderir, Shift+Enter satır atlar.
        </span>
        <Button type="submit" size="lg" disabled={bekleniyor || !girdi.trim()}>
          Gönder
        </Button>
      </div>
    </form>
  );
}

/** Onay formundaki tek bir alan (etiket + giriş). */
export function FormAlani({
  etiket,
  htmlFor,
  istegeBagli = false,
  children,
}: {
  etiket: string;
  htmlFor: string;
  istegeBagli?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium">
        {etiket}
        {istegeBagli ? (
          <span className="ml-1 font-normal text-muted-foreground">
            (isteğe bağlı)
          </span>
        ) : null}
      </label>
      {children}
    </div>
  );
}
