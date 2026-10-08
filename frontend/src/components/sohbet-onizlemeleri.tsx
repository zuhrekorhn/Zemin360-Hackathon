import { ToplananlarKutusu } from "@/components/kesif/toplananlar-kutusu";
import { KUTU } from "@/components/ui/yuzey";
import type { FirmaKartiTaslagi, IhtiyacTaslagi } from "@/lib/api";
import { isbirligiTuruEtiketi } from "@/lib/firma-karti";
import {
  ihtiyacToplananlari,
  firmaKartiToplananlari,
} from "@/lib/sohbet-onizleme";
import { cn } from "@/lib/utils";

/**
 * Firma sohbetleri sürerken sağdaki canlı önizleme (Keşif'teki
 * components/kesif/canli-onizleme.tsx'in eşi): üstte neyin toplandığı, altta
 * kartın o anki hali. Taslak onaylanmadan hiçbir şey kaydedilmez; bu yalnızca
 * önizleme. Firmaya "siz".
 */

function TaslakKutusu({
  etiket,
  baslik,
  children,
}: {
  etiket: string;
  baslik: string | null;
  children: React.ReactNode;
}) {
  return (
    <section
      aria-label={etiket}
      className={cn(KUTU, "flex flex-col gap-3 px-5 py-5")}
    >
      <p className="text-xs font-medium text-muted-foreground">{etiket}</p>
      <p
        className={cn(
          "font-heading text-lg leading-snug font-semibold",
          baslik ? "text-ana" : "text-muted-foreground italic",
        )}
      >
        {baslik ?? "Sohbet ilerledikçe belirecek"}
      </p>
      {children}
    </section>
  );
}

function Parca({
  etiket,
  metin,
}: {
  etiket: string;
  metin: string | null | undefined;
}) {
  if (!metin) return null;
  return (
    <div className="flex flex-col gap-0.5 border-t border-kenar pt-3 motion-safe:animate-in motion-safe:fade-in-0">
      <span className="text-xs text-muted-foreground">{etiket}</span>
      <span className="line-clamp-4 text-sm text-pretty">{metin}</span>
    </div>
  );
}

/** İhtiyaç sohbeti: problem kartın başlığı, ölçüt ve kısıtlar altında. */
export function IhtiyacOnizleme({
  taslak,
  ortak,
  firmaAdi,
}: {
  taslak: IhtiyacTaslagi | null;
  ortak: boolean;
  firmaAdi: string;
}) {
  const olcut = taslak?.basari_olcutu;
  const olcutParcalari = [
    olcut?.mevcut_deger ? `Bugün: ${olcut.mevcut_deger}` : null,
    olcut?.hedef_deger ? `Hedef: ${olcut.hedef_deger}` : null,
    olcut?.sure ? `Süre: ${olcut.sure}` : null,
  ].filter(Boolean);
  return (
    <div className="flex flex-col gap-4">
      <ToplananlarKutusu
        baslik="İhtiyacınızda olacaklar"
        ilerlemeEtiketi="İhtiyacınızın ne kadarı hazır"
        bilgiler={ihtiyacToplananlari(taslak, ortak)}
      />
      <TaslakKutusu
        etiket={firmaAdi || "İhtiyacınız oluşuyor"}
        baslik={taslak?.problem_tanimi ?? null}
      >
        <Parca etiket="Başarı ölçütü" metin={taslak?.basari_kriteri} />
        <Parca etiket="Ölçüt ayrıntısı" metin={olcutParcalari.join(" · ")} />
        <Parca etiket="Kısıtlar" metin={taslak?.kisitlar} />
        {ortak && taslak?.isbirligi_turu ? (
          <Parca
            etiket="İş birliği türü"
            metin={isbirligiTuruEtiketi(taslak.isbirligi_turu)}
          />
        ) : null}
        {taslak?.problem_tanimi ? null : (
          <p className="border-t border-kenar pt-3 text-xs text-pretty text-muted-foreground">
            Anlattıklarınız burada belirecek. Sohbetin sonunda ihtiyacı gözden
            geçirip onaylarsınız; onaylamadan kaydedilmez.
          </p>
        )}
      </TaslakKutusu>
    </div>
  );
}

/** Firma kartı sohbeti: "ne yapıyorsunuz" kartın başlığı. */
export function FirmaKartiOnizleme({
  taslak,
  firmaAdi,
}: {
  taslak: FirmaKartiTaslagi | null;
  firmaAdi: string;
}) {
  const yetkinlikler = taslak?.yetkinlikler ?? [];
  return (
    <div className="flex flex-col gap-4">
      <ToplananlarKutusu
        baslik="Kartınızda olacaklar"
        ilerlemeEtiketi="Kartınızın ne kadarı hazır"
        bilgiler={firmaKartiToplananlari(taslak)}
      />
      <TaslakKutusu
        etiket={firmaAdi || "Kartınız oluşuyor"}
        baslik={taslak?.ne_yapiyoruz ?? null}
      >
        {yetkinlikler.length > 0 ? (
          <ul className="flex flex-wrap gap-1.5 border-t border-kenar pt-3">
            {yetkinlikler.map((y) => (
              <li
                key={y}
                className="rounded-full bg-muted px-2.5 py-0.5 text-xs motion-safe:animate-in motion-safe:fade-in-0"
              >
                {y}
              </li>
            ))}
          </ul>
        ) : null}
        <Parca etiket="Önceki işler" metin={taslak?.onceki_isler} />
        <Parca etiket="Aradığınız ortak" metin={taslak?.aranan_isbirligi} />
        {taslak?.ne_yapiyoruz ? null : (
          <p className="border-t border-kenar pt-3 text-xs text-pretty text-muted-foreground">
            Anlattıklarınız burada belirecek. Sohbetin sonunda kartı gözden
            geçirip onaylarsınız; onaylamadan kaydedilmez.
          </p>
        )}
      </TaslakKutusu>
    </div>
  );
}
