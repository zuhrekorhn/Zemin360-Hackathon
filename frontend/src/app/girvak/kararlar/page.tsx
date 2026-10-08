"use client";

import { FirmaOnaylari } from "@/components/firma-onaylari";
import { IncelemeKuyrugu } from "@/components/inceleme-kuyrugu";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";

/** Karar bekleyenler: firma onayları ve inceleme kuyruğu. Karar GİRVAK'ın, sistem yalnızca ipucu verir. */
export default function GirvakKararlar() {
  return (
    <Sayfa>
      <SayfaBasligi
        baslik="Karar bekleyenler"
        aciklama="Onayınızı bekleyen firmalar ve sistemin işaretlediği kayıtlar. Karar verilen kayıt listeden çıkar."
      />
      <FirmaOnaylari />
      <IncelemeKuyrugu />
    </Sayfa>
  );
}
