"use client";

import { EslesmeHunisi } from "@/components/girvak/huni";
import { SayiGrubuBolumu } from "@/components/girvak/sayi-izgarasi";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { ListeIskeleti } from "@/components/ui/iskelet";
import { girvakSayilari } from "@/lib/api";
import { huniAdimlari, sayiGruplari } from "@/lib/girvak-sayilari";
import { useYukle } from "@/lib/yukle";

export default function GirvakSayilar() {
  const { veri: sayilar, hata, yenile } = useYukle(girvakSayilari);

  return (
    <Sayfa>
      <p className="hidden text-sm text-muted-foreground print:block">
        Zemin360 · GİRVAK raporu · {new Date().toLocaleDateString("tr-TR")}
      </p>
      <SayfaBasligi
        baslik="Sayılar"
        aciklama="Zemin360'ta şu ana kadar olanların dökümü: kaç hesap, kaç eşleşme, kaç iş birliği."
      />
      {hata ? (
        <HataKutusu hata={hata} tekrarDene={() => void yenile()} />
      ) : null}
      {sayilar === null && !hata ? <ListeIskeleti satir={3} /> : null}
      {sayilar ? <EslesmeHunisi adimlar={huniAdimlari(sayilar)} /> : null}
      {sayilar
        ? sayiGruplari(sayilar).map((grup) => (
            <SayiGrubuBolumu key={grup.kimlik} grup={grup} />
          ))
        : null}
      {sayilar ? (
        <div className="print:hidden">
          <Button
            type="button"
            variant="outline"
            onClick={() => window.print()}
          >
            Raporu yazdır
          </Button>
        </div>
      ) : null}
    </Sayfa>
  );
}
