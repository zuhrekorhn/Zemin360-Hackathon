"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { BosDurum, PanelBolumu, tarihYaz } from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import {
  type OnayBekleyenFirma,
  girvakFirmaDogrula,
  girvakFirmalar,
} from "@/lib/api";
import { ipucuMetni } from "@/lib/firma-dogrulama";
import { FIRMA_TURLERI } from "@/lib/firma-profil";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { cn } from "@/lib/utils";

/**
 * GİRVAK: onay bekleyen firmalar (docs/kararlar.md F6).
 *
 * Sistem ipucu verir, karar GİRVAK'ın. "Onayla" firmaya bildirim gönderir;
 * "Şimdilik değil" sessizdir. Tam e-posta gösterilmez, yalnızca uzantısı.
 */
export function FirmaOnaylari({ onKarar }: { onKarar?: () => void }) {
  const [firmalar, setFirmalar] = useState<OnayBekleyenFirma[] | null>(null);
  const [isleniyor, setIsleniyor] = useState<string | null>(null);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      setFirmalar(await girvakFirmalar());
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, []);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku();
  }, [oku]);

  async function karar(
    kurumId: string,
    secim: "dogrulandi" | "simdilik_degil",
  ) {
    setHata(null);
    setIsleniyor(kurumId);
    try {
      await girvakFirmaDogrula(kurumId, secim);
      onKarar?.();
      // Karar verilen firma listeden çıkar.
      setFirmalar(
        (liste) => liste?.filter((f) => f.kurum_id !== kurumId) ?? null,
      );
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setIsleniyor(null);
    }
  }

  return (
    <PanelBolumu
      id="firma-onaylari"
      baslik="Onay bekleyen firmalar"
      aciklama="Firmanın kayıtta yazdığı e-posta adresinin web sitesiyle uyuşup uyuşmadığına bakıyoruz (siteye girmeden). Bu yalnızca bir ipucu, karar sizin. Onayla: firmaya bildirim gider ve adının yanında “Doğrulanmış firma” görünür. Şimdilik değil: firmaya bir şey gitmez, firma “Doğrulama bekleniyor” görmeye devam eder."
    >
      {hata ? <HataKutusu hata={hata} tekrarDene={() => void oku()} /> : null}
      {firmalar === null ? null : firmalar.length === 0 ? (
        <BosDurum metin="Onay bekleyen firma yok." />
      ) : (
        <ul className="flex flex-col divide-y divide-kenar overflow-hidden rounded-xl border border-kenar bg-card">
          {firmalar.map((firma) => {
            const ipucu = ipucuMetni(firma.ipucu, firma.eposta_alan_adi);
            const tur = FIRMA_TURLERI.find((t) => t.deger === firma.tur);
            return (
              <li
                key={firma.kurum_id}
                className="flex flex-col gap-2 px-4 py-3"
              >
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <span className="font-medium text-ana">{firma.ad}</span>
                  <span className="text-xs text-muted-foreground">
                    {[tur?.etiket, firma.sektor, firma.sehir]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {tarihYaz(firma.kayit_tarihi)}
                  </span>
                </div>
                {firma.web_sitesi ? (
                  <span className="text-sm break-all">{firma.web_sitesi}</span>
                ) : null}
                <p
                  className={cn(
                    "text-sm text-pretty",
                    ipucu.olumlu ? "text-baglanti" : "text-muted-foreground",
                  )}
                >
                  {ipucu.metin}
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    disabled={isleniyor !== null}
                    onClick={() => void karar(firma.kurum_id, "dogrulandi")}
                  >
                    Onayla
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={isleniyor !== null}
                    onClick={() => void karar(firma.kurum_id, "simdilik_degil")}
                  >
                    Şimdilik değil
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </PanelBolumu>
  );
}
