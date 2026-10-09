/**
 * Taslak onayının alta yapışık şeridi: uzun formda sayfanın sonuna inmek
 * gerekmesin. Genç kartı onayı ve firmanın ihtiyaç onayı aynı şeridi kullanır
 * (docs/design-language.md § Yerleşim); düğme `<form>` içinde gönderir.
 */
export function OnayCubugu({
  metin,
  etiket,
  bekleniyor,
  bekleniyorEtiketi = "Kaydediliyor…",
}: {
  metin: string;
  etiket: string;
  bekleniyor: boolean;
  bekleniyorEtiketi?: string;
}) {
  return (
    <div className="sticky bottom-4 z-20">
      <div className="flex flex-col gap-3 rounded-xl bg-ana px-6 py-4 text-zemin shadow-[0_12px_32px_-16px_rgb(22_33_27/0.6)] sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-pretty text-zemin/85">{metin}</p>
        <button
          type="submit"
          disabled={bekleniyor}
          className="inline-flex h-10 shrink-0 items-center justify-center rounded-lg bg-vurgu px-5 text-sm font-semibold text-metin outline-none hover:bg-vurgu/90 focus-visible:ring-3 focus-visible:ring-zemin/60 disabled:opacity-60"
        >
          {bekleniyor ? bekleniyorEtiketi : etiket}
        </button>
      </div>
    </div>
  );
}
