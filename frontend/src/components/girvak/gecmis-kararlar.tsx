"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { KapaliBolum } from "@/components/kapali-bolum";
import { DurumEtiketi, tarihYaz } from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { KUTU } from "@/components/ui/yuzey";
import {
  type OnayBekleyenFirma,
  girvakFirmaDogrula,
  girvakFirmalar,
} from "@/lib/api";
import { FIRMA_TURLERI } from "@/lib/firma-profil";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { cn } from "@/lib/utils";

/**
 * GİRVAK: daha önce firmalara verdiğiniz kararlar. "Şimdilik değil" dediğiniz
 * firma onay listesinden çıkıyordu ve tekrar bakacağınız bir yer yoktu; burada
 * durur ve oradan onaylanabilir. Doğrulanan firma geri alınmaz (firmaya
 * bildirim gitmiştir). `surum` değişince liste yeniden okunur.
 */
export function GecmisKararlar({
  surum,
  onKarar,
}: {
  surum: number;
  onKarar: () => void;
}) {
  const [firmalar, setFirmalar] = useState<OnayBekleyenFirma[] | null>(null);
  const [isleniyor, setIsleniyor] = useState<string | null>(null);
  const [hata, setHata] = useState<Hata | null>(null);

  const oku = useCallback(async () => {
    try {
      const [dogrulanan, simdilikDegil] = await Promise.all([
        girvakFirmalar("dogrulandi"),
        girvakFirmalar("simdilik_degil"),
      ]);
      setHata(null);
      // En yeni karar önce.
      setFirmalar(
        [...simdilikDegil, ...dogrulanan].sort((a, b) =>
          (b.dogrulama_tarihi ?? "").localeCompare(a.dogrulama_tarihi ?? ""),
        ),
      );
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, []);

  // Aynı sürüm için bir kez oku (StrictMode efekti iki kez çalıştırır).
  const okunanSurum = useRef<number | null>(null);
  useEffect(() => {
    if (okunanSurum.current === surum) return;
    okunanSurum.current = surum;
    void oku();
  }, [oku, surum]);

  async function onayla(kurumId: string) {
    setHata(null);
    setIsleniyor(kurumId);
    try {
      await girvakFirmaDogrula(kurumId, "dogrulandi");
      onKarar();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setIsleniyor(null);
    }
  }

  if (hata) {
    return <HataKutusu hata={hata} tekrarDene={() => void oku()} />;
  }
  if (firmalar === null || firmalar.length === 0) return null;

  return (
    <KapaliBolum
      baslik="Daha önce verdiğiniz kararlar"
      sayi={firmalar.length}
      listeSinifi="flex flex-col gap-3"
    >
      {firmalar.map((firma) => {
        const tur = FIRMA_TURLERI.find((t) => t.deger === firma.tur);
        const dogrulandi = firma.dogrulama_durumu === "dogrulandi";
        return (
          <li
            key={firma.kurum_id}
            className={cn(KUTU, "flex flex-col gap-2 px-4 py-3")}
          >
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="font-medium text-ana">{firma.ad}</span>
              <span className="text-xs text-muted-foreground">
                {[tur?.etiket, firma.sektor, firma.sehir]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
              <span className="ml-auto flex items-center gap-2">
                <DurumEtiketi
                  metin={dogrulandi ? "Doğrulandı" : "Şimdilik değil"}
                  baglanti={dogrulandi}
                />
                <span className="text-xs text-muted-foreground">
                  {tarihYaz(firma.dogrulama_tarihi)}
                </span>
              </span>
            </div>
            {dogrulandi ? null : (
              <div className="flex flex-wrap items-center gap-3">
                <Button
                  type="button"
                  size="sm"
                  disabled={isleniyor !== null}
                  onClick={() => void onayla(firma.kurum_id)}
                >
                  Onayla
                </Button>
                <span className="text-xs text-muted-foreground">
                  Onaylarsanız firmaya bildirim gider ve adının yanında
                  “Doğrulanmış firma” görünür.
                </span>
              </div>
            )}
          </li>
        );
      })}
    </KapaliBolum>
  );
}
