import type { ReactNode } from "react";

/**
 * GİRVAK sayfalarının ortak düzeni: solda sakin bir yan sütun (özet ve
 * açıklama kutuları), sağda ana içerik. Genç ve firma panelleriyle aynı
 * iskelet (docs/design-language.md § Sayfa Düzeni); dar ekranda yan sütun
 * ana içeriğin altına iner.
 */
export function IkiSutun({
  yan,
  children,
}: {
  yan: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="grid items-start gap-8 lg:grid-cols-[19rem_minmax(0,1fr)]">
      <aside className="order-2 flex flex-col gap-4 lg:sticky lg:top-24 lg:order-1">
        {yan}
      </aside>
      <div className="order-1 flex min-w-0 flex-col gap-8 lg:order-2">
        {children}
      </div>
    </div>
  );
}
