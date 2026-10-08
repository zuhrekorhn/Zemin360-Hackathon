/**
 * "Neden uygun?" örneği. Gerçek ekranlardaki BelgeKarti: `KUTU` yüzeyi,
 * satırlar hairline çizgiyle (design-language.md § Sayfa Düzeni).
 *
 * Seviye yalnızca renge dayanmaz: kelime (Zayıf/Orta/Güçlü) her zaman
 * görünür, çubuğun kendi aria-label'ı var.
 */

import { BelgeKarti } from "@/components/kart";
import { SeviyeCubugu as Cubuk } from "@/components/seviye-cubugu";
import { SEFFAF, SEVIYE_KELIMELERI, type Seviye } from "@/content/landing";

import { OrnekRozeti } from "./demo-karti";

function SeviyeCubugu({ seviye }: { seviye: Seviye }) {
  const kelime = SEVIYE_KELIMELERI[seviye];
  return (
    <div className="flex shrink-0 items-center gap-3">
      <Cubuk seviye={seviye} etiket={`Seviye: ${kelime}`} buyuk />
      <span aria-hidden="true" className="w-14 text-right text-[15px] font-semibold text-metin">
        {kelime}
      </span>
    </div>
  );
}

export function NedenUygunOrnegi() {
  const { kart } = SEFFAF;
  return (
    <div className="flex flex-col gap-3">
      <BelgeKarti
        baslik={kart.baslik}
        altbaslik={kart.altbaslik}
        rozet={<OrnekRozeti>{kart.rozet}</OrnekRozeti>}
        etek={
          <ul className="divide-y divide-kenar/70">
            {kart.satirlar.map((satir) => (
              <li
                key={satir.baslik}
                className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:gap-5"
              >
                <div className="flex min-w-0 flex-col gap-1">
                  <p className="font-semibold text-metin">{satir.baslik}</p>
                  <p className="text-sm leading-snug text-muted-foreground">
                    {satir.metin}
                  </p>
                </div>
                <SeviyeCubugu seviye={satir.seviye} />
              </li>
            ))}
          </ul>
        }
      />
      <p className="text-sm text-pretty text-muted-foreground">{SEFFAF.not}</p>
    </div>
  );
}
