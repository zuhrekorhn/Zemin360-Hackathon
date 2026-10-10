"use client";

import { AlanKartiOgesi } from "@/components/girvak/alan-karti";
import { BekleyenlerKutusu } from "@/components/girvak/bekleyenler";
import { PanelBolumu } from "@/components/panel";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import { ListeIskeleti } from "@/components/ui/iskelet";
import { girvakOzet } from "@/lib/api";
import { alanKartlari } from "@/lib/girvak";
import { useYukle } from "@/lib/yukle";

/**
 * GİRVAK özeti (docs/canlilik.md § 7): önce sizi bekleyen kararlar, sonra
 * programın altı ihtiyaç alanı için Zemin360'ın durumu, brifteki adlarıyla.
 * Uydurma hedef yok; yalnızca gerçek sayılar. Kişisel veri yalnızca ad.
 */
export default function GirvakOzet() {
  const { veri: ozet, hata, yenile } = useYukle(girvakOzet);

  return (
    <Sayfa genislik="genis">
      <SayfaBasligi
        baslik="Özet"
        aciklama="Programın nerede olduğunu ve sizden bekleyen kararları buradan görürsünüz. Kişisel bilgi olarak yalnızca ad görünür; e-posta adresleri size hiç gösterilmez."
      />

      <BekleyenlerKutusu />

      {hata ? (
        <HataKutusu hata={hata} tekrarDene={() => void yenile()} />
      ) : null}
      {ozet === null && !hata ? <ListeIskeleti satir={3} /> : null}

      {ozet ? (
        <PanelBolumu
          id="alanlar"
          baslik="Altı ihtiyaç alanı"
          aciklama="Programın altı ihtiyaç alanı için Zemin360'ın şu anki durumu. Her kartın altındaki bağlantı ayrıntıya götürür."
        >
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {alanKartlari(ozet).map((alan) => (
              <AlanKartiOgesi key={alan.no} alan={alan} />
            ))}
          </ul>
        </PanelBolumu>
      ) : null}
    </Sayfa>
  );
}
