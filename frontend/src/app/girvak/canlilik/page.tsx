"use client";

import { useState } from "react";

import {
  KontrolKutusu,
  PasifBaglantilar,
  SonHatirlatmalar,
  TakilmaSureleri,
} from "@/components/girvak/canlilik";
import { IkiSutun } from "@/components/girvak/iki-sutun";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import {
  type TaramaSonucu,
  canlilikOlaylari,
  pasifBaglantilar,
  taramaCalistir,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { useYukle } from "@/lib/yukle";

/**
 * Takılan süreçler: kontrolü başlat (yan sütun), takılanları ve gönderilen
 * hatırlatmaları gör (ana içerik).
 */
export default function GirvakCanlilik() {
  const pasifler = useYukle(pasifBaglantilar);
  const olaylar = useYukle(canlilikOlaylari);
  const [sonuc, setSonuc] = useState<TaramaSonucu | null>(null);
  const [taraniyor, setTaraniyor] = useState(false);
  const [taramaHatasi, setTaramaHatasi] = useState<Hata | null>(null);

  async function tara() {
    setTaramaHatasi(null);
    setTaraniyor(true);
    try {
      setSonuc(await taramaCalistir());
      await Promise.all([pasifler.yenile(), olaylar.yenile()]);
    } catch (sebep) {
      setTaramaHatasi(hatayaCevir(sebep));
    } finally {
      setTaraniyor(false);
    }
  }

  const hata = taramaHatasi ?? pasifler.hata ?? olaylar.hata;

  return (
    <Sayfa genislik="genis">
      <SayfaBasligi
        baslik="Takılan süreçler"
        aciklama="Cevap beklerken ya da ilerlemeden duran süreçler ve onlara gönderilen hatırlatmalar."
      />
      {hata ? (
        <HataKutusu
          hata={hata}
          tekrarDene={() => {
            setTaramaHatasi(null);
            void pasifler.yenile();
            void olaylar.yenile();
          }}
        />
      ) : null}
      <IkiSutun
        yan={
          <>
            <KontrolKutusu
              taraniyor={taraniyor}
              sonuc={sonuc}
              onCalistir={() => void tara()}
            />
            <TakilmaSureleri />
          </>
        }
      >
        <PasifBaglantilar pasifler={pasifler.veri} />
        <SonHatirlatmalar olaylar={olaylar.veri} />
      </IkiSutun>
    </Sayfa>
  );
}
