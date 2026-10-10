"use client";

import { BekleyenlerKutusu } from "@/components/girvak/bekleyenler";
import { HedefKarti } from "@/components/girvak/hedef-karti";
import { PanelBolumu } from "@/components/panel";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import { ListeIskeleti } from "@/components/ui/iskelet";
import { girvakSayilari } from "@/lib/api";
import { useYukle } from "@/lib/yukle";

/**
 * GİRVAK genel bakışı (docs/canlilik.md § 7): önce sizi bekleyen kararlar, sonra
 * program hedefleri programın kendi adıyla ve platformda neyi saydığımızla; aradaki
 * fark gizlenmez. Ayrıntılar menüdeki öteki sayfalarda. Kişisel veri yalnızca ad.
 */
export default function GirvakGenelBakis() {
  const { veri: sayilar, hata, yenile } = useYukle(girvakSayilari);

  return (
    <Sayfa>
      <SayfaBasligi
        baslik="Özet"
        aciklama="Programın nerede olduğunu ve sizden bekleyen kararları buradan görürsünüz. Kişisel bilgi olarak yalnızca ad görünür; e-posta adresleri size hiç gösterilmez."
      />

      <BekleyenlerKutusu />

      {hata ? (
        <HataKutusu hata={hata} tekrarDene={() => void yenile()} />
      ) : null}
      {sayilar === null && !hata ? <ListeIskeleti satir={3} /> : null}

      {sayilar ? (
        <PanelBolumu
          id="hedefler"
          baslik="Program hedefleri"
          aciklama="Hedefler programın kendi adlarıyla yazıldı. Her kartın altında Zemin360'ın bu hedef için neyi saydığı yazıyor; programın tanımıyla birebir aynı olmayabilir."
        >
          <ul className="grid gap-4 sm:grid-cols-2">
            {sayilar.hedefler.map((hedef) => (
              <HedefKarti key={hedef.anahtar} hedef={hedef} />
            ))}
          </ul>
        </PanelBolumu>
      ) : null}
    </Sayfa>
  );
}
