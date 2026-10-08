"use client";

import { ChevronRight } from "lucide-react";

import { PilotRozeti } from "@/components/kart";
import { Button } from "@/components/ui/button";
import { KUTU } from "@/components/ui/yuzey";
import { adGosterimi } from "@/lib/ad";
import type { YetenekKartiYaniti } from "@/lib/api";
import type { Eksik, KartAdimi } from "@/lib/calisma";
import { kalanCumlesi, kartDurumu } from "@/lib/calisma";
import { DENEYIM_ETIKETLERI, etiketle } from "@/lib/sabitler";
import { cn } from "@/lib/utils";

/**
 * Kart sayfasının sol sütunu ve sayfa düzeyindeki "Sıradaki adım" bandı
 * (docs/kararlar.md G18). Kartın durumu tek bir puana indirilmez
 * (docs/agent-specs.md § 4): eksik başlıklar sayılır, çalışma çalışma gösterilir.
 */

/** Kullanıcının yazdığı rolün ilk harfi büyük: "backend geliştirici" → "Backend geliştirici". */
export function cumleDuzeni(metin: string): string {
  return metin.charAt(0).toLocaleUpperCase("tr") + metin.slice(1);
}

/** Adın baş harfleri: "Elif Demir" → "ED". */
export function basHarfler(ad: string): string {
  return ad
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((parca) => parca.charAt(0).toLocaleUpperCase("tr"))
    .join("");
}

function Etiketler({
  baslik,
  degerler,
}: {
  baslik: string;
  degerler: string[];
}) {
  if (degerler.length === 0) return null;
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs text-muted-foreground">{baslik}</span>
      <ul className="flex flex-wrap gap-1.5">
        {degerler.map((deger) => (
          <li
            key={deger}
            className="rounded-full bg-muted px-2.5 py-0.5 text-xs text-metin"
          >
            {deger}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Kartın kimliği: firmaların gördüğü ad, rol, deneyim ve etiketler. */
export function KimlikKutusu({
  kart,
  onDuzenle,
}: {
  kart: YetenekKartiYaniti;
  onDuzenle: () => void;
}) {
  return (
    <section className={cn(KUTU, "flex flex-col gap-4 px-5 py-5")}>
      <div className="flex items-center gap-3">
        <span
          aria-hidden="true"
          className="flex size-12 shrink-0 items-center justify-center rounded-full bg-ana font-heading text-base font-semibold text-zemin"
        >
          {basHarfler(kart.genc_adi)}
        </span>
        <div className="flex min-w-0 flex-col">
          <span className="font-heading text-lg leading-tight font-semibold text-ana">
            {adGosterimi(kart.genc_adi)}
          </span>
          <span className="text-sm text-metin">
            {cumleDuzeni(kart.rol_alani)}
          </span>
          <span className="text-xs text-muted-foreground">
            Deneyim: {etiketle(DENEYIM_ETIKETLERI, kart.deneyim_seviyesi)}
          </span>
        </div>
      </div>
      <PilotRozeti sayi={kart.tamamlanan_pilot} />
      <Etiketler baslik="Araçlar" degerler={kart.araclar_teknolojiler} />
      <Etiketler baslik="Sektör ilgisi" degerler={kart.sektor_ilgi_alani} />
      <Etiketler baslik="Sertifikalar" degerler={kart.sertifikalar} />
      <Etiketler baslik="Diller" degerler={kart.diller} />
      <div className="flex flex-col gap-2 border-t border-kenar pt-4">
        <Button
          type="button"
          variant="outline"
          className="w-fit"
          onClick={onDuzenle}
        >
          Kartı düzenle
        </Button>
        <p className="text-xs text-pretty text-muted-foreground">
          Firmalar seni bu kartla, adınla birlikte görür. E-postan yalnızca
          karşılıklı ilgi oluşunca paylaşılır.
        </p>
      </div>
    </section>
  );
}

/** Kartın durumu: kaç başlık eksik, çalışma çalışma. Puan değil, sayım. */
export function KartDurumuKutusu({
  calismalar,
  onSec,
}: {
  calismalar: { id: string; baslik: string; eksikler: Eksik[] }[];
  onSec: (id: string) => void;
}) {
  const durum = kartDurumu(calismalar.map((c) => c.eksikler));
  if (durum.calisma === 0) return null;
  return (
    <section className={cn(KUTU, "flex flex-col gap-3 px-5 py-5")}>
      <h2 className="font-heading text-base font-semibold text-ana">
        Kartının durumu
      </h2>
      <p className="flex items-baseline gap-2">
        <span
          className={cn(
            "font-heading text-2xl font-semibold",
            durum.eksik > 0 ? "text-ana" : "text-baglanti",
          )}
        >
          {durum.eksik > 0 ? `${durum.eksik} eksik` : "Eksik yok"}
        </span>
        <span className="text-sm text-muted-foreground">
          {durum.calisma} çalışma
          {durum.tamam > 0 ? ` · ${durum.tamam} eksiksiz` : ""}
        </span>
      </p>
      <ul className="flex flex-col">
        {calismalar.map((calisma) => (
          <li key={calisma.id}>
            <button
              type="button"
              onClick={() => onSec(calisma.id)}
              className="-mx-2 flex w-[calc(100%+1rem)] items-center gap-3 rounded-md px-2 py-1.5 text-left hover:bg-muted"
            >
              <span className="min-w-0 flex-1 truncate text-sm">
                {calisma.baslik}
              </span>
              <span
                className={cn(
                  "shrink-0 text-xs",
                  calisma.eksikler.length > 0
                    ? "font-medium text-metin"
                    : "text-baglanti",
                )}
              >
                {calisma.eksikler.length > 0
                  ? `${calisma.eksikler.length} eksik`
                  : "Tamam"}
              </span>
              <ChevronRight
                aria-hidden="true"
                className="size-4 shrink-0 text-muted-foreground"
              />
            </button>
          </li>
        ))}
      </ul>
      <p className="text-xs text-pretty text-muted-foreground">
        Firmalar sana uygun fırsatlarda bu göstergelere bakar. Eksikleri
        tamamladıkça öne çıkarsın.
      </p>
    </section>
  );
}

const BASLIK_ANLAMLARI = [
  [
    "Kanıt",
    "Çalışmayı gösteren link ya da dosya; çalışmanın sana ait olduğu görülüyor mu.",
  ],
  ["Sonuç", "Çalışmanın ne sağladığı; sayıyla anlatıldıysa daha güçlü."],
  ["Rol", "Bu çalışmada senin ne yaptığın; ekipçe yapıldıysa hangi kısmı."],
  ["Referans", "Çalışmanı bilen birinin e-postayla verdiği yanıt."],
] as const;

/** "Dört başlık ne anlama geliyor?": güven göstergesinin açıklaması (rehber § 9.5). */
export function BasliklarAciklamasi() {
  return (
    <details className={cn(KUTU, "group px-5 py-4")}>
      <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-medium text-ana">
        <ChevronRight
          aria-hidden="true"
          className="size-4 transition-transform group-open:rotate-90"
        />
        Dört başlık ne anlama geliyor?
      </summary>
      <dl className="mt-3 flex flex-col gap-2.5">
        {BASLIK_ANLAMLARI.map(([ad, metin]) => (
          <div key={ad} className="flex flex-col gap-0.5">
            <dt className="text-sm font-medium">{ad}</dt>
            <dd className="text-sm text-pretty text-muted-foreground">
              {metin}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-pretty text-muted-foreground">
        Kanıt, sonuç ve rol yapay zekâ desteğiyle değerlendirilir; referans
        puanını referans kişi verir. Değerlendirmeyi eksik bulursan itiraz
        edebilirsin.
      </p>
    </details>
  );
}

/** Sayfa düzeyinde tek öneri: en az eksiği kalan çalışmanın ilk eksiği. */
export function SiradakiAdimBandi({
  adim,
  onAc,
}: {
  adim: KartAdimi;
  onAc: () => void;
}) {
  return (
    <section
      aria-label="Sıradaki adım"
      className="flex flex-col gap-4 rounded-xl bg-ana px-6 py-5 text-zemin sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex min-w-0 flex-col gap-1">
        <p className="truncate text-xs font-medium text-zemin/70">
          Sıradaki adım · {adim.calisma}
        </p>
        <p className="font-heading text-xl leading-snug font-semibold text-balance">
          {adim.adim.kisa}
        </p>
        <p className="text-sm text-pretty text-zemin/80">
          {kalanCumlesi(adim)}
        </p>
      </div>
      <button
        type="button"
        onClick={onAc}
        className="inline-flex h-10 shrink-0 items-center justify-center self-start rounded-lg bg-vurgu px-4 text-sm font-semibold text-metin outline-none hover:bg-vurgu/90 focus-visible:ring-3 focus-visible:ring-zemin/60 sm:self-center"
      >
        {adim.adim.etiket}
      </button>
    </section>
  );
}
