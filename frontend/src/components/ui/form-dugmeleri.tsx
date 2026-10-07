"use client";

import { Button } from "@/components/ui/button";

/** Formun gönder düğmesi ve (verilirse) vazgeç düğmesi. */
export function FormDugmeleri({
  children,
  onVazgec,
}: {
  children: React.ReactNode;
  /** Form her zaman açıksa (Güçlendir paneli) verilmez. */
  onVazgec?: () => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {children}
      {onVazgec ? (
        <Button type="button" size="sm" variant="ghost" onClick={onVazgec}>
          Vazgeç
        </Button>
      ) : null}
    </div>
  );
}
