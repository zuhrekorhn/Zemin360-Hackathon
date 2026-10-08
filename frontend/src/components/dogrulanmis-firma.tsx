import { DOGRULANMIS_FIRMA } from "@/lib/firma-dogrulama";

/**
 * "Doğrulanmış firma" işareti (docs/kararlar.md F17).
 * Firma adının geçtiği yerde, yalnızca GİRVAK doğruladıysa görünür.
 */
export function DogrulanmisFirma({ dogrulandi }: { dogrulandi: boolean }) {
  if (!dogrulandi) return null;
  return (
    <span className="rounded-full bg-baglanti/10 px-2.5 py-0.5 text-xs font-medium text-baglanti">
      {DOGRULANMIS_FIRMA}
    </span>
  );
}
