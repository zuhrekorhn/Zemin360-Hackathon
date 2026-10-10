"use client";

import { useState } from "react";

import { FirmaOnaylari } from "@/components/firma-onaylari";
import { GecmisKararlar } from "@/components/girvak/gecmis-kararlar";
import { IncelemeKuyrugu } from "@/components/inceleme-kuyrugu";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";

/**
 * Karar bekleyenler: firma onayları ve incelemeler; altta daha önce verilen
 * kararlar. Karar GİRVAK'ın, sistem yalnızca ipucu verir.
 */
export default function GirvakKararlar() {
  // Bir karar verilince geçmiş liste yeniden okunur ("şimdilik değil" orada görünür).
  const [surum, setSurum] = useState(0);
  const kararVerildi = () => setSurum((onceki) => onceki + 1);

  return (
    <Sayfa>
      <SayfaBasligi
        baslik="Karar bekleyenler"
        aciklama="Kararınızı bekleyen firmalar ve sistemin kontrol edilmesini istediği kayıtlar. Karar verdiğiniz kayıt listeden çıkar."
      />
      <FirmaOnaylari onKarar={kararVerildi} />
      <IncelemeKuyrugu />
      <GecmisKararlar surum={surum} onKarar={kararVerildi} />
    </Sayfa>
  );
}
