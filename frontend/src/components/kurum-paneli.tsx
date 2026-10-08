"use client";

import Link from "next/link";

import { BekleyenKabi, YanKutu } from "@/components/genc-paneli";
import { IlanKapatma } from "@/components/ilan-kapatma";
import { basHarfler } from "@/components/kart-yan-sutunu";
import { EylemMenusu } from "@/components/eylem-menusu";
import { DurumEtiketi, tarihYaz } from "@/components/panel";
import { Button } from "@/components/ui/button";
import { KUTU } from "@/components/ui/yuzey";
import type { IhtiyacKartiOzeti, KurumOnerisi } from "@/lib/api";
import { arananEtiketi, ilanKapali } from "@/lib/ilan";
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
          <span className="text-sm text-muted-foreground">
            {kartVar ? "Firma kartınız yayında" : "Firma kartınız henüz yok"}
          </span>
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

/** Adayların tek listesi: her satırda tek durum etiketi, tıklayınca ihtiyacın aday sayfası. */
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
                  <DurumEtiketi
                    metin={satir.etiket}
                    baglanti={satir.baglanti}
                  />
                </span>
                <span className="truncate text-xs text-muted-foreground">
                  {satir.alt}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {gizli > 0 ? (
        <p className="text-xs text-muted-foreground">
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
  kapatiliyor,
  onDuzenle,
  onKapatmaAc,
  onKapatmaBirak,
  onKapandi,
}: {
  kart: IhtiyacKartiOzeti;
  sayi: IhtiyacSayilari | undefined;
  kapatiliyor: boolean;
  onDuzenle: () => void;
  onKapatmaAc: () => void;
  onKapatmaBirak: () => void;
  onKapandi: () => void;
}) {
  const kapali = ilanKapali(kart);
  const sayim = sayimMetni(sayi);
  const aranan = arananEtiketi(kart.aranan);
  return (
    <li
      className={cn(
        KUTU,
        "flex flex-col overflow-hidden",
        kapali && "bg-transparent shadow-none",
      )}
    >
      <div className="flex flex-col gap-3 px-6 pt-5 pb-4">
        <div className="flex items-start justify-between gap-3">
          <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            {tarihYaz(kart.olusturma_tarihi)}
            {aranan ? <DurumEtiketi metin={aranan} /> : null}
            {kapali ? <DurumEtiketi metin="Kapandı" /> : null}
          </p>
          {kapali ? null : (
            <EylemMenusu
              etiket="Bu ihtiyaç için eylemler"
              eylemler={[
                { etiket: "Düzenle", onSec: onDuzenle },
                { etiket: "İhtiyacı kapat", onSec: onKapatmaAc, yikici: true },
              ]}
            />
          )}
        </div>
        <p
          className={cn(
            "line-clamp-4 text-[15px] leading-relaxed text-pretty",
            kapali && "text-muted-foreground",
          )}
        >
          {kart.problem_tanimi}
        </p>
        {kart.basari_kriteri ? (
          <p className="line-clamp-2 text-sm text-pretty text-muted-foreground">
            <span className="font-medium text-metin">Başarı ölçütü: </span>
            {kart.basari_kriteri}
          </p>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-kenar px-6 py-3.5">
        <Button asChild size="lg" variant={kapali ? "outline" : "default"}>
          <Link href={`/kurum/oneriler?ihtiyac=${kart.id}`}>Adayları gör</Link>
        </Button>
        <span className="text-xs text-muted-foreground">
          {kapali
            ? "Bu ihtiyaç kapandı."
            : (sayim ??
              (kart.embedding_var
                ? "Henüz aday yok."
                : "Adayları açtığınızda uygun adaylar hazırlanır."))}
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
