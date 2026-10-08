"use client";

import { secimiDegistir } from "@/lib/secim";

/**
 * İşaret kutularıyla çoklu seçim (çalışma modeli, müsaitlik). Onay formu,
 * kayıt formu ve profil sayfası aynı parçayı kullanır.
 */
export function CokluSecim({
  baslik,
  ipucu,
  aciklama,
  secenekler,
  secili,
  onDegis,
}: {
  baslik: string;
  /** Başlığın yanında soluk yazı, ör. "(kabul ettiklerini işaretle)". */
  ipucu?: string;
  /** Kutuların altında küçük açıklama. */
  aciklama?: string;
  secenekler: readonly { deger: string; etiket: string }[];
  secili: string[];
  onDegis: (secili: string[]) => void;
}) {
  const degerler = secenekler.map((secenek) => secenek.deger);
  return (
    <fieldset className="flex flex-col gap-1.5 sm:col-span-2">
      <legend className="text-sm font-medium">
        {baslik}
        {ipucu ? (
          <span className="ml-1 font-normal text-muted-foreground">
            {ipucu}
          </span>
        ) : null}
      </legend>
      <div className="flex flex-wrap gap-2">
        {secenekler.map((secenek) => {
          const isaretli = secili.includes(secenek.deger);
          return (
            <label
              key={secenek.deger}
              className={
                isaretli
                  ? "flex cursor-pointer items-center gap-2 rounded-lg border border-baglanti bg-muted px-3 py-2 text-sm"
                  : "flex cursor-pointer items-center gap-2 rounded-lg border border-kenar bg-card px-3 py-2 text-sm"
              }
            >
              <input
                type="checkbox"
                checked={isaretli}
                onChange={() =>
                  onDegis(secimiDegistir(degerler, secili, secenek.deger))
                }
                className="accent-baglanti"
              />
              {secenek.etiket}
            </label>
          );
        })}
      </div>
      {aciklama ? (
        <p className="text-xs text-muted-foreground">{aciklama}</p>
      ) : null}
    </fieldset>
  );
}
