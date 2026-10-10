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
        baslik="Sayılar"
        aciklama="Zemin360'ta şu ana kadar olanların dökümü: kaç hesap, kaç eşleşme, kaç iş birliği."
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
