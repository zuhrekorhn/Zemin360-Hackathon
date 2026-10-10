import { PanelBolumu } from "@/components/panel";
import { KUTU } from "@/components/ui/yuzey";
import type { HuniAdimi } from "@/lib/girvak-sayilari";
import { cn } from "@/lib/utils";

/**
 * Eşleşmenin yolu: öneriden tamamlanan iş birliğine, her adımda kaçı kalıyor.
 * Çubuk ilk adıma göre, yüzde bir önceki adıma göre (dönüşüm). Boşsa söyler.
 */
export function EslesmeHunisi({ adimlar }: { adimlar: HuniAdimi[] }) {
  const bos = adimlar.length === 0 || adimlar[0].sayi === 0;
  return (
    <PanelBolumu
      id="huni"
      baslik="Eşleşmenin yolu"
      aciklama="Önerilen eşleşmelerin kaçı iki tarafın ilgisine, iş birliğine ve tamamlanmaya ulaştı. Yüzde, bir önceki adıma göredir."
    >
      {bos ? (
        <p className="text-sm text-muted-foreground">
          Henüz önerilen bir eşleşme yok.
        </p>
      ) : (
        <ol className={cn(KUTU, "flex flex-col gap-4 px-5 py-5")}>
          {adimlar.map((adim) => (
            <li key={adim.etiket} className="flex flex-col gap-1.5">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <span className="text-sm font-medium text-ana">
                  {adim.etiket}
                </span>
                <span className="flex items-baseline gap-2">
                  <span className="font-heading text-2xl font-semibold text-ana">
                    {adim.sayi}
                  </span>
                  {adim.oncekineGore !== null ? (
                    <span className="text-xs text-muted-foreground">
                      %{adim.oncekineGore}
                    </span>
                  ) : null}
                </span>
              </div>
              <div
                className="h-1.5 w-full overflow-hidden rounded-full bg-kenar"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={adim.genislik}
                aria-label={adim.etiket}
              >
                <div
                  className="h-full rounded-full bg-baglanti"
                  style={{ width: `${adim.genislik}%` }}
                />
              </div>
            </li>
          ))}
        </ol>
      )}
    </PanelBolumu>
  );
}
