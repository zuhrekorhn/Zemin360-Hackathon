"use client";

import { SayiGrubuBolumu } from "@/components/girvak/sayi-izgarasi";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import { ListeIskeleti } from "@/components/ui/iskelet";
import { girvakSayilari } from "@/lib/api";
import { sayiGruplari } from "@/lib/girvak-sayilari";
import { useYukle } from "@/lib/yukle";

export default function GirvakSayilar() {
  const { veri: sayilar, hata, yenile } = useYukle(girvakSayilari);

  return (
    <Sayfa>
      <SayfaBasligi
        baslik="Platform sayıları"
        aciklama="Hesaplar, eşleşmeler ve iş birliklerinin dökümü."
      />
      {hata ? (
        <HataKutusu hata={hata} tekrarDene={() => void yenile()} />
      ) : null}
      {sayilar === null && !hata ? <ListeIskeleti satir={3} /> : null}
      {sayilar
        ? sayiGruplari(sayilar).map((grup) => (
            <SayiGrubuBolumu key={grup.kimlik} grup={grup} />
          ))
        : null}
    </Sayfa>
  );
}
