"use client";

import { useState } from "react";

import { DogrulanmisFirma } from "@/components/dogrulanmis-firma";
import { Button } from "@/components/ui/button";
import type { GencEslesmesi, IhtiyacKartiYaniti } from "@/lib/api";
import {
  ILETISIM_ONAYI,
  ILETISIM_ONAYI_KUTUSU,
  NEDEN_UYGUN,
  uyumMetni,
} from "@/lib/ilgi";
import {
  CALISMA_MODELI_ETIKETLERI,
  MUSAITLIK_ETIKETLERI,
  etiketle,
  sehirEtiketi,
} from "@/lib/sabitler";

/**
 * Gencin ana sayfasındaki fırsat kartı (docs/api-contracts.md). Metinler
 * docs/icerik-rehberi.md'ye göre: uyum kelimeyle, "Neden uygun?" gence
 * yazılmış metinle (docs/kararlar.md G9; yoksa bölüm hiç çizilmez).
 */

/** İhtiyacın koşulları: şehir, çalışma modeli, müsaitlik. */
export function KosulEtiketleri({ ihtiyac }: { ihtiyac: IhtiyacKartiYaniti }) {
  const kosullar = [
    ihtiyac.sehir_tercihi ? sehirEtiketi(ihtiyac.sehir_tercihi) : null,
    ihtiyac.calisma_modeli
      ? etiketle(CALISMA_MODELI_ETIKETLERI, ihtiyac.calisma_modeli)
      : null,
    ihtiyac.musaitlik_tercihi
      ? etiketle(MUSAITLIK_ETIKETLERI, ihtiyac.musaitlik_tercihi)
      : null,
  ].filter((k): k is string => Boolean(k));
  if (kosullar.length === 0) return null;
  return (
    <ul className="flex flex-wrap gap-1.5" aria-label="Koşullar">
      {kosullar.map((kosul) => (
        <li
          key={kosul}
          className="rounded-full border border-kenar px-2.5 py-0.5 text-xs text-muted-foreground"
        >
          {kosul}
        </li>
      ))}
    </ul>
  );
}

/** Firma adı ve doğrulanmış işareti; fırsat ve ilgi kartlarının başlığı. */
export function FirmaBasligi({
  ihtiyac,
  sag,
}: {
  ihtiyac: IhtiyacKartiYaniti;
  sag?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
      <h3 className="flex flex-wrap items-center gap-2 font-heading text-lg leading-snug font-semibold text-ana">
        {ihtiyac.kurum.ad}
        <DogrulanmisFirma dogrulandi={ihtiyac.kurum.dogrulandi} />
      </h3>
      {sag}
    </div>
  );
}

/** Bir fırsat: firma, uyum, ihtiyaç, "Neden uygun?" ve açık onaylı "İlgileniyorum". */
export function FirsatKarti({
  firsat,
  onIlgi,
}: {
  firsat: GencEslesmesi;
  onIlgi: () => Promise<void>;
}) {
  const [onayAcik, setOnayAcik] = useState(false);
  const [onaylandi, setOnaylandi] = useState(false);
  const [bekleniyor, setBekleniyor] = useState(false);
  const ihtiyac = firsat.ihtiyac_karti;

  async function ilet() {
    if (!onaylandi || bekleniyor) return;
    setBekleniyor(true);
    try {
      await onIlgi();
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <li className="flex flex-col rounded-md border border-kenar bg-card">
      <div className="flex flex-col gap-3 px-5 pt-5 pb-4">
        <FirmaBasligi
          ihtiyac={ihtiyac}
          sag={
            <span className="rounded-full bg-baglanti/10 px-2.5 py-1 text-xs font-medium text-baglanti">
              {uyumMetni(firsat.uyum)}
            </span>
          }
        />
        <KosulEtiketleri ihtiyac={ihtiyac} />
        <p className="text-[15px] leading-relaxed text-pretty text-metin">
          {ihtiyac.problem_tanimi}
        </p>
        {ihtiyac.basari_kriteri ? (
          <p className="text-sm text-pretty text-muted-foreground">
            <span className="font-medium text-metin">Başarı ölçütü: </span>
            {ihtiyac.basari_kriteri}
          </p>
        ) : null}
        {firsat.gerekce_metni ? (
          <section className="flex flex-col gap-1 rounded-sm border-l-2 border-baglanti bg-zemin px-4 py-3">
            <h4 className="font-heading text-sm font-semibold text-ana">
              {NEDEN_UYGUN}
            </h4>
            <p className="text-sm leading-relaxed text-pretty">
              {firsat.gerekce_metni}
            </p>
          </section>
        ) : null}
      </div>

      <div className="border-t border-kenar px-5 py-3">
        {!onayAcik ? (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <Button type="button" size="lg" onClick={() => setOnayAcik(true)}>
              İlgileniyorum
            </Button>
            <span className="text-xs text-pretty text-muted-foreground">
              Firma da ilgilenirse iletişim bilgileriniz paylaşılır.
            </span>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-pretty">{ILETISIM_ONAYI}</p>
            <label className="flex w-fit items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={onaylandi}
                onChange={(olay) => setOnaylandi(olay.target.checked)}
                className="size-4 accent-ana"
              />
              {ILETISIM_ONAYI_KUTUSU}
            </label>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="lg"
                disabled={!onaylandi || bekleniyor}
                onClick={() => void ilet()}
              >
                {bekleniyor ? "İletiliyor…" : "İlgimi ilet"}
              </Button>
              <Button
                type="button"
                size="lg"
                variant="ghost"
                disabled={bekleniyor}
                onClick={() => {
                  setOnayAcik(false);
                  setOnaylandi(false);
                }}
              >
                Vazgeç
              </Button>
            </div>
          </div>
        )}
      </div>
    </li>
  );
}
