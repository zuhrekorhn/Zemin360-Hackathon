"use client";

import { ArrowUp } from "lucide-react";
import { useEffect, useRef } from "react";

import { Button } from "@/components/ui/button";
import { hitapla } from "@/lib/hitap";
import { useHitap } from "@/lib/oturum";

/**
 * Keşif ve Tanımlama sohbetlerinin paylaştığı iki görsel parça.
 *
 * Görsel dil (docs/design-language.md): balonlar yuvarlak/sıcak, hata kutusu
 * hairline çizgili. Sohbet akışının mantığı (durum, istekler) paylaşılmıyor —
 * her ajanın kendi sayfasında duruyor.
 */

export type Mesaj = { kim: "ajan" | "kullanici"; metin: string };

/** Tek cevabın üst sınırı: backend'deki `CEVAP_EN_COK` ile aynı (app/schemas/sohbet.py). */
export const CEVAP_EN_COK = 6000;

export type SohbetHatasi = { metin: string; kota: boolean };

export function Sohbet({
  ajanAdi,
  mesajlar,
  bekleniyor,
  sonMesajRef,
  altKisim,
}: {
  ajanAdi: string;
  mesajlar: Mesaj[];
  bekleniyor: boolean;
  sonMesajRef: React.RefObject<HTMLDivElement | null>;
  /** Sohbet kutusunun altına yapışan yazma alanı. */
  altKisim?: React.ReactNode;
}) {
  const kutu = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = kutu.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [mesajlar, bekleniyor]);

  return (
    <div className="flex flex-col overflow-hidden rounded-[1.75rem] border border-kenar bg-card shadow-[0_1px_2px_rgb(22_33_27/0.05)]">
      {/* Mesajlar kendi içinde kayar, yazma alanı hep görünür; yeni mesajda en alta inilir. */}
      <section
        ref={kutu}
        aria-label="Sohbet"
        aria-live="polite"
        className="flex h-[min(62vh,640px)] min-h-72 flex-col gap-4 overflow-y-auto overscroll-contain bg-muted/50 px-4 py-5 sm:px-6"
      >
        {mesajlar.map((mesaj, sira) =>
          mesaj.kim === "ajan" ? (
            <div
              key={`ajan-${sira}`}
              className="flex max-w-[88%] items-end gap-2.5"
            >
              <span
                aria-hidden="true"
                className="flex size-8 shrink-0 items-center justify-center rounded-full bg-ana font-heading text-sm font-semibold text-zemin"
              >
                Z
              </span>
              <p className="rounded-3xl rounded-bl-lg bg-card px-4 py-3 text-[15px] leading-relaxed text-pretty break-words whitespace-pre-line ring-1 ring-kenar">
                <span className="mb-0.5 block text-xs font-medium text-baglanti">
                  {ajanAdi}
                </span>
                {mesaj.metin}
              </p>
            </div>
          ) : (
            <p
              key={`kullanici-${sira}`}
              className="ml-auto max-w-[80%] rounded-3xl rounded-br-lg bg-ana px-4 py-3 text-[15px] leading-relaxed text-pretty break-words whitespace-pre-line text-zemin"
            >
              {mesaj.metin}
            </p>
          ),
        )}

        {bekleniyor ? (
          <div className="flex items-end gap-2.5">
            <span
              aria-hidden="true"
              className="flex size-8 shrink-0 items-center justify-center rounded-full bg-ana font-heading text-sm font-semibold text-zemin"
            >
              Z
            </span>
            <p className="flex items-center gap-1.5 rounded-3xl rounded-bl-lg bg-card px-4 py-3.5 ring-1 ring-kenar">
              <span className="sr-only">Yanıt hazırlanıyor…</span>
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  aria-hidden="true"
                  style={{ animationDelay: `${i * 150}ms` }}
                  className="size-2 rounded-full bg-baglanti/70 motion-safe:animate-pulse"
                />
              ))}
            </p>
          </div>
        ) : null}

        <div ref={sonMesajRef} />
      </section>
      {altKisim ? (
        <div className="border-t border-kenar bg-card p-3 sm:p-4">
          {altKisim}
        </div>
      ) : null}
    </div>
  );
}

/**
 * `tekrarDene` verilmezse buton çizilmez: 404/409 gibi hatalarda aynı isteği
 * tekrarlamak sonucu değiştirmiyor, buton boş bir umut oluyor.
 */
export function HataKutusu({
  hata,
  tekrarDene,
}: {
  hata: SohbetHatasi;
  tekrarDene?: () => void;
}) {
  const hitap = useHitap();
  return (
    <div
      role="status"
      className="flex flex-col gap-3 rounded-xl border border-kenar bg-card px-5 py-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="text-sm text-pretty">{hata.metin}</p>
      {tekrarDene ? (
        <Button
          type="button"
          variant="outline"
          size="lg"
          onClick={tekrarDene}
          className="w-fit shrink-0"
        >
          {hitapla(hitap, "Tekrar dene", "Tekrar deneyin")}
        </Button>
      ) : null}
    </div>
  );
}

/**
 * Sohbet giriş alanı: Enter gönderir, Shift+Enter satır atlar. Sohbet
 * kutusunun altına yapışık durur (`Sohbet` › `altKisim`); düğme alanın içinde.
 */
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
  const hitap = useHitap();
  return (
    <form
      onSubmit={(olay) => {
        olay.preventDefault();
        gonder();
      }}
      className="flex flex-col gap-2"
    >
      <label htmlFor="cevap" className="sr-only">
        {hitapla(hitap, "Yanıtın", "Yanıtınız")}
      </label>
      <div className="flex items-end gap-2 rounded-2xl border border-kenar bg-zemin/60 p-2 focus-within:border-baglanti focus-within:ring-3 focus-within:ring-baglanti/25">
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
          rows={2}
          maxLength={CEVAP_EN_COK}
          disabled={bekleniyor}
          placeholder={hitapla(hitap, "Yazmaya başla…", "Yazmaya başlayın…")}
          // Yazdıkça büyür (field-sizing), 12rem'den sonra kendi içinde kayar.
          className="field-sizing-content max-h-48 min-h-12 flex-1 resize-none overflow-y-auto bg-transparent px-2 py-1.5 text-[15px] leading-relaxed outline-none disabled:opacity-60"
        />
        <Button
          type="submit"
          size="icon-lg"
          disabled={bekleniyor || !girdi.trim()}
          aria-label={hitapla(hitap, "Yanıtı gönder", "Yanıtı gönderin")}
          className="rounded-xl"
        >
          <ArrowUp aria-hidden="true" />
        </Button>
      </div>
      <span className="flex items-center justify-between gap-3 px-1 text-xs text-muted-foreground">
        <span>Enter gönderir, Shift+Enter satır atlar.</span>
        {girdi.length > CEVAP_EN_COK * 0.8 ? (
          <span
            role="status"
            className={
              girdi.length >= CEVAP_EN_COK ? "font-medium text-destructive" : ""
            }
          >
            {girdi.length}/{CEVAP_EN_COK}
            {girdi.length >= CEVAP_EN_COK ? " · en fazla bu kadar yazılır" : ""}
          </span>
        ) : null}
      </span>
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
