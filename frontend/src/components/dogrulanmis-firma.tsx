import { DOGRULANMIS_FIRMA } from "@/lib/firma-dogrulama";

/**
 * "Doğrulanmış firma" işareti (docs/plans/firma-akisi.md § 0 karar 17).
 * Firma adının geçtiği yerde, yalnızca GİRVAK doğruladıysa görünür.
 */
export function DogrulanmisFirma({ dogrulandi }: { dogrulandi: boolean }) {
  if (!dogrulandi) return null;
  return (
    <span className="rounded-sm border border-baglanti px-2 py-0.5 text-xs text-baglanti">
      {DOGRULANMIS_FIRMA}
    </span>
  );
}
