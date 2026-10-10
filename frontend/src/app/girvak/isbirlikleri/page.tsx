"use client";

import { useState } from "react";

import { GirvakIsbirligiSatiri } from "@/components/girvak/isbirligi-satiri";
import { BosDurum } from "@/components/panel";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { ListeIskeleti } from "@/components/ui/iskelet";
import { girvakIsbirlikleri } from "@/lib/api";
import {
  ISBIRLIGI_FILTRELERI,
  type IsbirligiFiltresi,
  bosFiltreMetni,
  filtreSayilari,
  filtrele,
} from "@/lib/girvak";
import { isbirligiSirasi } from "@/lib/takip";
import { useYukle } from "@/lib/yukle";

/**
 * GİRVAK: bütün iş birlikleri (programın "şeffaf iş birliği takibi" alanı).
 * Plan onayı bekleyenler, süren, gecikmiş ve tamamlananlar tek yerde; satırdan
 * iş birliğinin kendi sayfasına geçilir. Kişisel iletişim bilgisi gösterilmez.
 */
export default function GirvakIsbirlikleri() {
  const { veri, hata, yenile } = useYukle(girvakIsbirlikleri);
  const [filtre, setFiltre] = useState<IsbirligiFiltresi>("hepsi");

  const sayilar = veri ? filtreSayilari(veri) : null;
  const gorunen = veri ? isbirligiSirasi(filtrele(veri, filtre)) : [];

  return (
    <Sayfa genislik="genis">
      <SayfaBasligi
        baslik="İş birlikleri"
        aciklama="Zemin360'ta açılan bütün iş birlikleri. Planı, adımların ilerleyişini ve takılanları buradan izlersiniz; kişisel iletişim bilgisi gösterilmez."
      />

      {hata ? (
        <HataKutusu hata={hata} tekrarDene={() => void yenile()} />
      ) : null}
      {veri === null && !hata ? <ListeIskeleti satir={3} /> : null}

      {veri && sayilar ? (
        <>
          <div
            className="flex flex-wrap items-center gap-2"
            role="group"
            aria-label="İş birliklerini süz"
          >
            {ISBIRLIGI_FILTRELERI.map((f) => (
              <Button
                key={f.deger}
                type="button"
                size="sm"
                variant={f.deger === filtre ? "default" : "outline"}
                aria-pressed={f.deger === filtre}
                onClick={() => setFiltre(f.deger)}
              >
                {f.etiket} ({sayilar[f.deger]})
              </Button>
            ))}
          </div>

          {gorunen.length === 0 ? (
            <BosDurum metin={bosFiltreMetni(filtre)} />
          ) : (
            <ul className="grid gap-4 lg:grid-cols-2">
              {gorunen.map((isbirligi) => (
                <GirvakIsbirligiSatiri
                  key={isbirligi.isbirligi_id}
                  isbirligi={isbirligi}
                />
              ))}
            </ul>
          )}
        </>
      ) : null}
    </Sayfa>
  );
}
