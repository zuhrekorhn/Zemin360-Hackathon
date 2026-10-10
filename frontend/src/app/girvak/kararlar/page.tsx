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
        aciklama="Kararınızı bekleyen firmalar ve sistemin kontrol edilmesini istediği kayıtlar. Karar verdiğiniz kayıt listeden çıkar."
      />
      <FirmaOnaylari />
      <IncelemeKuyrugu />
    </Sayfa>
  );
}
