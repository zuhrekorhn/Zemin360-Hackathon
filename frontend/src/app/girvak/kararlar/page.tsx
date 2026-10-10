"use client";

import { useState } from "react";

import { FirmaOnaylari } from "@/components/firma-onaylari";
import { YanKutu } from "@/components/genc-paneli";
import { GecmisKararlar } from "@/components/girvak/gecmis-kararlar";
import { IkiSutun } from "@/components/girvak/iki-sutun";
import { IncelemeKuyrugu } from "@/components/inceleme-kuyrugu";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";

/**
 * Karar bekleyenler: firma onayları ve incelemeler; altta daha önce verilen
 * kararlar. Karar GİRVAK'ın, sistem yalnızca ipucu verir. Düğmelerin ne
 * yaptığı yan sütunda sabit durur (karar verirken göz önünde olsun).
 */
export default function GirvakKararlar() {
  // Bir karar verilince geçmiş liste yeniden okunur ("şimdilik değil" orada görünür).
  const [surum, setSurum] = useState(0);
  const kararVerildi = () => setSurum((onceki) => onceki + 1);

  return (
    <Sayfa genislik="genis">
      <SayfaBasligi
        baslik="Karar bekleyenler"
        aciklama="Kararınızı bekleyen firmalar ve sistemin kontrol edilmesini istediği kayıtlar. Karar verdiğiniz kayıt listeden çıkar."
      />
      <IkiSutun yan={<KararRehberi />}>
        <FirmaOnaylari onKarar={kararVerildi} />
        <IncelemeKuyrugu />
        <GecmisKararlar surum={surum} onKarar={kararVerildi} />
      </IkiSutun>
    </Sayfa>
  );
}

/** Düğmelerin sonucu: karar vermeden önce bilinmesi gereken şey. */
function KararRehberi() {
  return (
    <>
      <YanKutu baslik="Firma onayı">
        <dl className="flex flex-col gap-3 text-sm">
          <div className="flex flex-col gap-0.5">
            <dt className="font-medium text-ana">Onayla</dt>
            <dd className="text-pretty text-muted-foreground">
              Firmaya bildirim gider, adının yanında “Doğrulanmış firma”
              görünür.
            </dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="font-medium text-ana">Şimdilik değil</dt>
            <dd className="text-pretty text-muted-foreground">
              Firmaya bir şey gitmez; firma “Doğrulama bekleniyor” görmeye devam
              eder. Kararı sonra değiştirebilirsiniz.
            </dd>
          </div>
        </dl>
      </YanKutu>
      <YanKutu baslik="İnceleme">
        <dl className="flex flex-col gap-3 text-sm">
          <div className="flex flex-col gap-0.5">
            <dt className="font-medium text-ana">Sorun yok</dt>
            <dd className="text-pretty text-muted-foreground">
              İnceleme kapanır, genç bilgilendirilir.
            </dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="font-medium text-ana">Doğrulanamadı</dt>
            <dd className="text-pretty text-muted-foreground">
              İlgili çalışma “doğrulanamadı” olarak işaretlenir; genç bunu görür
              ve itiraz edebilir.
            </dd>
          </div>
        </dl>
        <p className="border-t border-kenar pt-3 text-xs text-pretty text-muted-foreground">
          Hiçbir durum güven göstergesini kendiliğinden düşürmez. E-posta
          adresleri size gösterilmez; firmalarda yalnızca uzantısı, gençlerde
          yalnızca ad görünür.
        </p>
      </YanKutu>
    </>
  );
}
