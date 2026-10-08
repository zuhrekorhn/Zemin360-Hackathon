/**
 * Hesabım ve Firma profili gibi uzun formların bölümü: hairline çizgiyle
 * ayrılır, yan menüdeki bağlantı `id`'ye gider. Bölümler bir `KUTU` içinde dizilir.
 */
export function FormBolumu({
  id,
  children,
}: {
  id?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      id={id}
      className="scroll-mt-24 border-t border-kenar px-6 py-6 first:border-t-0"
    >
      {children}
    </div>
  );
}
