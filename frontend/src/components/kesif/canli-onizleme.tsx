import { ToplananlarKutusu } from "@/components/kesif/toplananlar-kutusu";
import { KUTU } from "@/components/ui/yuzey";
import type { KartTaslagi } from "@/lib/api";
import { toplananlar } from "@/lib/kesif";
import { DENEYIM_ETIKETLERI, etiketle } from "@/lib/sabitler";
import { cn } from "@/lib/utils";

/**
 * Keşif sohbeti sürerken kartın canlı hali (lib/kesif.ts). Genç neyin
 * sorulacağını ve ne kadar kaldığını görür; her yanıtla kart dolar. Taslak
 * onaylanmadan hiçbir şey kaydedilmez, bu yalnızca önizleme.
 */
export function CanliOnizleme({
  taslak,
  ad,
}: {
  taslak: KartTaslagi | null;
  ad: string;
}) {
  return (
    <div className="flex flex-col gap-4">
      <ToplananlarKutusu
        baslik="Kartında olacaklar"
        ilerlemeEtiketi="Kartın ne kadarı hazır"
        bilgiler={toplananlar(taslak)}
      />

      <section
        aria-label="Kartının taslağı"
        className={cn(KUTU, "flex flex-col gap-3 px-5 py-5")}
      >
        <p className="text-xs font-medium text-muted-foreground">
          Kartın oluşuyor
        </p>
        <div className="flex flex-col gap-0.5">
          <span className="font-heading text-lg leading-tight font-semibold text-ana">
            {ad}
          </span>
          <span
            className={cn(
              "text-sm",
              taslak?.rol_alani ? "text-metin" : "text-muted-foreground italic",
            )}
          >
            {taslak?.rol_alani ?? "Rolün sohbette netleşecek"}
          </span>
          {taslak?.deneyim_seviyesi ? (
            <span className="text-xs text-muted-foreground">
              Deneyim: {etiketle(DENEYIM_ETIKETLERI, taslak.deneyim_seviyesi)}
            </span>
          ) : null}
        </div>
        {(taslak?.araclar_teknolojiler.length ?? 0) > 0 ? (
          <ul className="flex flex-wrap gap-1.5">
            {taslak?.araclar_teknolojiler.map((arac) => (
              <li
                key={arac}
                className="rounded-full bg-muted px-2.5 py-0.5 text-xs motion-safe:animate-in motion-safe:fade-in-0"
              >
                {arac}
              </li>
            ))}
          </ul>
        ) : null}
        {(taslak?.somut_ciktilar.length ?? 0) > 0 ? (
          <ul className="flex flex-col gap-2 border-t border-kenar pt-3">
            {taslak?.somut_ciktilar.map((cikti, i) => (
              <li
                key={i}
                className="flex flex-col gap-0.5 motion-safe:animate-in motion-safe:fade-in-0"
              >
                <span className="text-sm font-medium">{cikti.baslik}</span>
                {cikti.olculebilir_sonuc ? (
                  <span className="line-clamp-2 text-xs text-muted-foreground">
                    Sonuç: {cikti.olculebilir_sonuc}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="border-t border-kenar pt-3 text-xs text-pretty text-muted-foreground">
            Anlattığın çalışmalar burada belirecek. Sohbetin sonunda kartı
            gözden geçirip onaylarsın; onaylamadan kaydedilmez.
          </p>
        )}
      </section>
    </div>
  );
}
