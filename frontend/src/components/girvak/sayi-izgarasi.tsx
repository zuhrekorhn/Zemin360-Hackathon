import { PanelBolumu } from "@/components/panel";
import type { SayiGrubu } from "@/lib/girvak-sayilari";

/** Başlıklı sayı grubu: hairline ızgarada hizalı sayılar, dar ekranda iki sütun. */
export function SayiGrubuBolumu({ grup }: { grup: SayiGrubu }) {
  return (
    <PanelBolumu id={grup.kimlik} baslik={grup.baslik} aciklama={grup.aciklama}>
      <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-kenar bg-kenar shadow-[0_1px_2px_rgb(22_33_27/0.05)] sm:grid-cols-3">
        {grup.ogeler.map((oge) => (
          <div
            key={oge.etiket}
            className="flex flex-col gap-1 bg-card px-4 py-3"
          >
            <dt className="text-xs text-muted-foreground">{oge.etiket}</dt>
            <dd className="font-mono text-2xl text-ana">{oge.sayi}</dd>
          </div>
        ))}
      </dl>
    </PanelBolumu>
  );
}
