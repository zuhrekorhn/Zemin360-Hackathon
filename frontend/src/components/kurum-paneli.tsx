"use client";

import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";

import { BekleyenKabi, YanKutu } from "@/components/genc-paneli";
import { IlanKapatma } from "@/components/ilan-kapatma";
import { basHarfler } from "@/components/kart-yan-sutunu";
import { EylemMenusu } from "@/components/eylem-menusu";
import { DurumEtiketi, tarihYaz } from "@/components/panel";
import { Button } from "@/components/ui/button";
import { KUTU } from "@/components/ui/yuzey";
import type { IhtiyacKartiOzeti, KurumOnerisi } from "@/lib/api";
import { KAPILAR, arananEtiketi, ilanKapali } from "@/lib/ilan";
import {
  ADAY_LISTESI_SINIRI,
  type AdaySatiri,
  type IhtiyacSayilari,
  sayimMetni,
} from "@/lib/kurum-paneli";
import { cn } from "@/lib/utils";

/**
 * Firma panelinin parçaları (app/kurum/page.tsx). Kararlar lib/kurum-paneli.ts'de;
 * burada yalnızca çizim. Gencin ana sayfasıyla (components/genc-paneli.tsx)
 * aynı dil: yüzeyler `KUTU`, yanıt bekleyen iş vurgu renginde sol çizgiyle,
 * ikincil eylemler "⋯" menüsünde (docs/design-language.md § Sayfa Düzeni).
 */

/** Yan sütunun başı: firmanın adı ve firma kartına bağlantı. */
export function FirmaOzeti({ ad, kartVar }: { ad: string; kartVar: boolean }) {
  return (
    <section className={cn(KUTU, "flex flex-col gap-4 px-5 py-5")}>
      <div className="flex items-center gap-3">
        <span
          aria-hidden="true"
          className="flex size-12 shrink-0 items-center justify-center rounded-full bg-ana font-heading text-base font-semibold text-zemin"
        >
          {basHarfler(ad)}
        </span>
        <div className="flex min-w-0 flex-col">
          <span className="font-heading text-lg leading-tight font-semibold text-ana">
            {ad}
          </span>
          {kartVar ? (
            <span className="text-sm text-muted-foreground">
              Firma kartınız hazır
            </span>
          ) : null}
        </div>
      </div>
      {/* Kart yoksa çağrı "Tamamlanacaklar"da; burada tekrarlanmaz. */}
      {kartVar ? (
        <Button asChild variant="outline" className="w-full">
          <Link href="/kurum/kart">Firma kartınıza gidin</Link>
        </Button>
      ) : null}
    </section>
  );
}

/** Adayların tek listesi: etiket yalnızca bir şey söylüyorsa, tıklayınca ihtiyacın aday sayfası. */
export function AdayListesi({ satirlar }: { satirlar: AdaySatiri[] }) {
  const gorunen = satirlar.slice(0, ADAY_LISTESI_SINIRI);
  const gizli = satirlar.length - gorunen.length;
  return (
    <YanKutu baslik="Adaylarınız">
      {satirlar.length === 0 ? (
        <p className="text-sm text-pretty text-muted-foreground">
          Bir ihtiyacın adaylarını açtığınızda uygun adaylar burada listelenir.
        </p>
      ) : (
        <ul className="-mx-2 flex flex-col">
          {gorunen.map((satir) => (
            <li key={satir.anahtar}>
              <Link
                href={satir.hedef}
                className="flex flex-col gap-0.5 rounded-md px-2 py-2 hover:bg-muted"
              >
                <span className="flex items-center justify-between gap-3">
                  <span className="min-w-0 truncate text-sm font-medium">
                    {satir.ad}
                  </span>
                  {satir.etiket ? (
                    <DurumEtiketi
                      metin={satir.etiket}
                      baglanti={satir.baglanti}
                    />
                  ) : null}
                </span>
                <span className="truncate text-[13px] text-muted-foreground">
                  {satir.alt}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {gizli > 0 ? (
        <p className="text-sm text-muted-foreground">
          {gizli} aday daha var; ihtiyaç kartlarından açabilirsiniz.
        </p>
      ) : null}
    </YanKutu>
  );
}

/** Aday ilgi gösterdi: firmanın yanıtı bekleniyor. */
export function IlgiGosterenKarti({ oneri }: { oneri: KurumOnerisi }) {
  return (
    <BekleyenKabi>
      {/* Küçük metin vurgu renginde yazılmaz (kontrast); renk noktada. */}
      <p className="flex items-center gap-2 text-xs font-medium text-ana">
        <span aria-hidden="true" className="size-1.5 rounded-full bg-vurgu" />
        {oneri.aday_turu === "firma"
          ? "Bir firma ilgi gösterdi"
          : "Bir aday ilgi gösterdi"}
      </p>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="font-heading text-base font-semibold text-ana">
            {oneri.aday_adi}
          </span>
          <span className="line-clamp-1 text-sm text-muted-foreground">
            {oneri.problem_tanimi}
          </span>
        </div>
        <Button asChild size="lg">
          <Link href={`/kurum/oneriler?ihtiyac=${oneri.ihtiyac_karti_id}`}>
            Adayı gör
          </Link>
        </Button>
      </div>
    </BekleyenKabi>
  );
}

/** Bir ihtiyaç: problem, tek birincil eylem, ikincil eylemler "⋯" menüsünde. */
export function IhtiyacKarti({
  kart,
  sayi,
  tamamlanan = 0,
  kapatiliyor,
  onDuzenle,
  onKapatmaAc,
  onKapatmaBirak,
  onKapandi,
}: {
  kart: IhtiyacKartiOzeti;
  sayi: IhtiyacSayilari | undefined;
  /** Bu ihtiyaçtan tamamlanan iş birliği sayısı. */
  tamamlanan?: number;
  kapatiliyor: boolean;
  onDuzenle: () => void;
  onKapatmaAc: () => void;
  onKapatmaBirak: () => void;
  onKapandi: () => void;
}) {
  const kapali = ilanKapali(kart);
  const sayimParcasi = sayimMetni(sayi);
  const sayim =
    tamamlanan > 0
      ? [sayimParcasi, `${tamamlanan} tamamlanan iş birliği`]
          .filter(Boolean)
          .join(" · ")
      : sayimParcasi;
  const aranan = arananEtiketi(kart.aranan);
  return (
    <li
      className={cn(
        KUTU,
        "flex flex-col overflow-hidden",
        kapali && "bg-transparent shadow-none",
      )}
    >
      <div className="flex flex-col gap-3 px-6 pt-5 pb-5">
        <div className="flex min-h-9 items-start justify-between gap-3">
          <p className="flex flex-wrap items-center gap-2">
            {aranan ? <DurumEtiketi metin={aranan} /> : null}
            {kapali ? <DurumEtiketi metin="Kapandı" /> : null}
          </p>
          {kapali ? null : (
            <EylemMenusu
              etiket="Bu ihtiyaç için eylemler"
              eylemler={[
                { etiket: "Düzenle", onSec: onDuzenle },
                {
                  etiket: "İhtiyacı kapat",
                  onSec: onKapatmaAc,
                  yikici: true,
                },
              ]}
            />
          )}
        </div>
        <p
          className={cn(
            "line-clamp-4 text-base leading-relaxed text-pretty",
            kapali && "text-muted-foreground",
          )}
        >
          {kart.problem_tanimi}
        </p>
        {kart.basari_kriteri ? (
          <p className="line-clamp-2 text-sm leading-relaxed text-pretty text-muted-foreground">
            <span className="font-medium text-metin">Başarı ölçütü: </span>
            {kart.basari_kriteri}
          </p>
        ) : null}
        {tamamlanan > 0 && !kapali ? (
          <p className="rounded-lg bg-baglanti/[0.08] px-3 py-2 text-sm text-pretty">
            Bu ihtiyaç için bir iş birliği tamamlandı. İhtiyaç çözüldüyse “⋯”
            menüsünden kapatabilirsiniz.
          </p>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-kenar px-6 py-3.5">
        <Button asChild size="lg" variant={kapali ? "outline" : "default"}>
          <Link href={`/kurum/oneriler?ihtiyac=${kart.id}`}>Adayları gör</Link>
        </Button>
        <span className="text-sm text-muted-foreground">
          {kapali
            ? "Bu ihtiyaç kapandı."
            : (sayim ??
              (kart.embedding_var
                ? "Henüz aday yok."
                : "Adayları açtığınızda uygun adaylar hazırlanır."))}
        </span>
        <span className="ml-auto text-sm text-muted-foreground">
          {tarihYaz(kart.olusturma_tarihi)}
        </span>
      </div>
      {kapatiliyor && !kapali ? (
        <IlanKapatma
          kartId={kart.id}
          onKapandi={onKapandi}
          onVazgec={onKapatmaBirak}
        />
      ) : null}
    </li>
  );
}

/**
 * "Yeni ihtiyaç": iki kapı tek düğmenin arkasında, her biri ne işe yaradığını
 * söyleyerek (docs/kararlar.md F4, F9). Bölümün birincil eylemi bu; ekranda
 * iki eşdeğer düğme yarışmasın.
 */
export function YeniIhtiyacMenusu() {
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

  return (
    <div ref={kutu} className="relative">
      <Button
        ref={dugme}
        type="button"
        variant="outline"
        size="lg"
        aria-expanded={acik}
        aria-controls="yeni-ihtiyac-menusu"
        onClick={() => setAcik((onceki) => !onceki)}
      >
        Yeni ihtiyaç
        <ChevronDown
          aria-hidden="true"
          className={cn("transition-transform", acik && "rotate-180")}
        />
      </Button>
      {acik ? (
        <div
          id="yeni-ihtiyac-menusu"
          className="absolute top-full right-0 z-30 mt-2 flex w-72 flex-col gap-0.5 rounded-lg border border-kenar bg-card p-1.5 shadow-[0_8px_24px_-12px_rgb(22_33_27/0.25)]"
        >
          {KAPILAR.map((kapi) => (
            <Link
              key={kapi.aranan}
              href={kapi.yol}
              onClick={() => setAcik(false)}
              className="flex flex-col gap-0.5 rounded-md px-3 py-2.5 hover:bg-muted"
            >
              <span className="text-sm font-medium text-ana">
                {kapi.baslik}
              </span>
              <span className="text-[13px] leading-snug text-pretty text-muted-foreground">
                {kapi.aciklama}
              </span>
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}

/**
 * Açılır bölüm: panelde yalnızca güncel işler görünür, biten kayıtlar (kapanan
 * ihtiyaçlar, tamamlanan iş birlikleri) başlığın arkasında durur ve geçmişe
 * erişim korunur. `acik`: ilk durum (güncel iş kalmadıysa bitenler açık gelir).
 */
export function KapaliBolum({
  baslik,
  sayi,
  acik: ilkDurum = false,
  children,
}: {
  baslik: string;
  sayi: number;
  acik?: boolean;
  children: React.ReactNode;
}) {
  const [acik, setAcik] = useState(ilkDurum);
  const listeId = useId();
  return (
    <section aria-label={baslik} className="flex flex-col gap-4">
      <button
        type="button"
        aria-expanded={acik}
        aria-controls={listeId}
        onClick={() => setAcik((onceki) => !onceki)}
        className="inline-flex w-fit items-center gap-1.5 rounded-md text-sm font-medium text-muted-foreground outline-none hover:text-metin focus-visible:ring-3 focus-visible:ring-baglanti/40"
      >
        {baslik} ({sayi})
        <ChevronDown
          aria-hidden="true"
          className={cn("size-4 transition-transform", acik && "rotate-180")}
        />
      </button>
      {acik ? (
        <ul id={listeId} className="flex flex-col gap-4">
          {children}
        </ul>
      ) : null}
    </section>
  );
}
