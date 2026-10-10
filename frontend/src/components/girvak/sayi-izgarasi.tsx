import { PanelBolumu } from "@/components/panel";
import { KUTU } from "@/components/ui/yuzey";
import { cn } from "@/lib/utils";
import type { SayiGrubu } from "@/lib/girvak-sayilari";

/** Başlıklı sayı grubu: hairline ızgarada hizalı sayılar, dar ekranda iki sütun. */
export function SayiGrubuBolumu({ grup }: { grup: SayiGrubu }) {
  return (
    <PanelBolumu id={grup.kimlik} baslik={grup.baslik} aciklama={grup.aciklama}>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {grup.ogeler.map((oge) => (
          <div
            key={oge.etiket}
            className={cn(KUTU, "flex flex-col gap-1 px-4 py-3")}
          >
            <dt className="text-xs text-muted-foreground">{oge.etiket}</dt>
            <dd className="font-heading text-2xl font-semibold text-ana">
              {oge.sayi}
            </dd>
          </div>
        ))}
      </dl>
    </PanelBolumu>
  );
}
