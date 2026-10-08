import { KUTU } from "@/components/ui/yuzey";
import type { ProgramHedefi } from "@/lib/api";
import { hedefBasligi, hedefYuzdesi } from "@/lib/canlilik";
import { cn } from "@/lib/utils";

/** Program hedefi: programın adıyla başlık, büyük sayı, ilerleme çizgisi, altında bizim ölçümümüz. */
export function HedefKarti({ hedef }: { hedef: ProgramHedefi }) {
  const yuzde = hedefYuzdesi(hedef.sayi, hedef.hedef);
  const baslik = hedefBasligi(hedef.hedef, hedef.program_adi);
  return (
    <li className={cn(KUTU, "flex flex-col gap-3 px-5 py-5")}>
      <span className="text-sm font-medium text-pretty text-ana">{baslik}</span>
      <p className="flex items-baseline gap-1.5">
        <span className="font-mono text-4xl text-ana">{hedef.sayi}</span>
        <span className="font-mono text-base text-muted-foreground">
          / {hedef.hedef}
        </span>
      </p>
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-kenar"
        role="progressbar"
        aria-valuenow={hedef.sayi}
        aria-valuemin={0}
        aria-valuemax={hedef.hedef}
        aria-label={baslik}
      >
        <div className="h-full bg-baglanti" style={{ width: `${yuzde}%` }} />
      </div>
      <span className="text-xs text-pretty text-muted-foreground">
        Platformda: {hedef.olcum}
      </span>
    </li>
  );
}
