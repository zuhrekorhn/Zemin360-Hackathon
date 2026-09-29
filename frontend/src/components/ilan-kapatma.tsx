"use client";

import { useId, useState } from "react";

import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { ihtiyacKartiKapat } from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { KAPANMA_NEDENLERI, type KapanmaNedeni } from "@/lib/ilan";

/**
 * İlanı kapatma (docs/plans/firma-akisi.md § 0 karar 7, § 7).
 *
 * Tarayıcının onay penceresi değil, sayfa içi alan: rehber § 5.6 eylem adlı
 * butonlar istiyor ("Kapat" / "Vazgeç") ve neden seçimi aynı yerde. Firmaya "siz".
 */
export function IlanKapatma({
  kartId,
  onKapandi,
}: {
  kartId: string;
  onKapandi: () => void;
}) {
  const [acik, setAcik] = useState(false);
  const [neden, setNeden] = useState<KapanmaNedeni | null>(null);
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);
  const ad = useId();

  if (!acik) {
    return (
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="w-fit shrink-0"
        onClick={() => setAcik(true)}
      >
        İhtiyacı kapat
      </Button>
    );
  }

  async function kapat() {
    if (!neden || bekleniyor) return;
    setHata(null);
    setBekleniyor(true);
    try {
      await ihtiyacKartiKapat(kartId, neden);
      onKapandi();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
      setBekleniyor(false);
    }
  }

  return (
    <div className="flex w-full flex-col gap-3 rounded-sm border border-kenar bg-muted px-4 py-3 text-sm">
      <p className="text-pretty">
        Bu ihtiyaç kapatılsın mı? Bekleyen adaylara “fırsat kapandı” bildirimi
        gider ve yeni aday aranmaz. Kapanan ihtiyaç tekrar açılmaz.
      </p>
      <fieldset className="flex flex-col gap-1.5">
        <legend className="mb-1 font-medium">Neden kapatıyorsunuz?</legend>
        {KAPANMA_NEDENLERI.map((secenek) => (
          <label key={secenek.deger} className="flex items-center gap-2">
            <input
              type="radio"
              name={ad}
              value={secenek.deger}
              checked={neden === secenek.deger}
              onChange={() => setNeden(secenek.deger)}
              className="accent-ana"
            />
            {secenek.etiket}
          </label>
        ))}
        <span className="text-xs text-muted-foreground">
          Nedeni yalnızca program ekibi görür; adaylara gösterilmez.
        </span>
      </fieldset>
      {hata ? <HataKutusu hata={hata} /> : null}
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          disabled={!neden || bekleniyor}
          onClick={() => void kapat()}
        >
          {bekleniyor ? "Kapatılıyor…" : "Kapat"}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={bekleniyor}
          onClick={() => {
            setAcik(false);
            setNeden(null);
            setHata(null);
          }}
        >
          Vazgeç
        </Button>
      </div>
    </div>
  );
}
