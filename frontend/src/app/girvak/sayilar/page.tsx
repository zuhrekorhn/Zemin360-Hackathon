"use client";

import { EslesmeHunisi } from "@/components/girvak/huni";
import { IkiSutun } from "@/components/girvak/iki-sutun";
import {
  SayiGrubuBolumu,
  SayiYanKutusu,
} from "@/components/girvak/sayi-izgarasi";
import { YanKutu } from "@/components/genc-paneli";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { ListeIskeleti } from "@/components/ui/iskelet";
import { girvakSayilari } from "@/lib/api";
import { huniAdimlari, sayiGruplari } from "@/lib/girvak-sayilari";
import { useYukle } from "@/lib/yukle";

export default function GirvakSayilar() {
  const { veri: sayilar, hata, yenile } = useYukle(girvakSayilari);
  const gruplar = sayilar ? sayiGruplari(sayilar) : [];
  const hesaplar = gruplar.find((g) => g.kimlik === "hesaplar");
  const digerleri = gruplar.filter((g) => g.kimlik !== "hesaplar");

  return (
    <Sayfa genislik="genis">
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
      {sayilar ? (
        <IkiSutun
          yan={
            <>
              {hesaplar ? <SayiYanKutusu grup={hesaplar} /> : null}
              <YanKutu baslik="Rapor" className="print:hidden">
                <p className="text-sm text-pretty text-muted-foreground">
                  Bu sayfayı tarih başlığıyla yazdırabilir ya da PDF olarak
                  kaydedebilirsiniz.
                </p>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => window.print()}
                >
                  Raporu yazdır
                </Button>
              </YanKutu>
            </>
          }
        >
          <EslesmeHunisi adimlar={huniAdimlari(sayilar)} />
          {digerleri.map((grup) => (
            <SayiGrubuBolumu key={grup.kimlik} grup={grup} />
          ))}
        </IkiSutun>
      ) : null}
    </Sayfa>
  );
}
