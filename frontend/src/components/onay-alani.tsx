"use client";

import { Button } from "@/components/ui/button";

/**
 * Sayfa içi onay (docs/icerik-rehberi.md § 5.6). Tarayıcının kendi penceresi
 * "Tamam / İptal" yazıyor ve metni değiştirilemiyor; rehber eylemin adını
 * istiyor ("Sil" / "Vazgeç"). Soru eylemin sonucunu söyler.
 */
export function OnayAlani({
  soru,
  onayEtiketi,
  vazgecEtiketi = "Vazgeç",
  bekleniyor = false,
  bekleniyorEtiketi,
  onOnayla,
  onVazgec,
}: {
  soru: string;
  onayEtiketi: string;
  vazgecEtiketi?: string;
  bekleniyor?: boolean;
  bekleniyorEtiketi?: string;
  onOnayla: () => void;
  onVazgec: () => void;
}) {
  return (
    <div
      role="alertdialog"
      aria-label={soru}
      className="flex w-full flex-col gap-3 rounded-lg border border-kenar bg-muted px-4 py-3 text-sm"
    >
      <p className="text-pretty">{soru}</p>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          disabled={bekleniyor}
          onClick={onOnayla}
        >
          {bekleniyor && bekleniyorEtiketi ? bekleniyorEtiketi : onayEtiketi}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={bekleniyor}
          onClick={onVazgec}
        >
          {vazgecEtiketi}
        </Button>
      </div>
    </div>
  );
}
