"use client";

import { useState } from "react";

import { FormAlani } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { notuBasliklaraAyir } from "@/lib/guven-gostergesi";

/**
 * GİRVAK'ın "doğrulanamadı" kararı (docs/dogrulama.md § 9). Puanı değiştirmez; genç kararı
 * görür ve itiraz edebilir. GİRVAK "sorun yok" derse etiket kalkar.
 */
export function DogrulanamadiEtiketi({ notlar }: { notlar: string[] }) {
  return (
    <section
      className="flex flex-col gap-1.5 rounded-sm border border-kenar px-3 py-2"
      aria-label="GİRVAK kararı"
    >
      <span className="w-fit rounded-sm border border-kenar px-2 py-0.5 text-xs font-medium">
        Doğrulanamadı
      </span>
      <p className="text-sm text-pretty">
        GİRVAK bu çalışmayı inceledi ve şimdilik doğrulayamadı. Güven göstergen
        bu yüzden değişmedi; karara aşağıdan itiraz edebilirsin.
      </p>
      {notlar.map((not, i) => (
        <p key={i} className="text-sm text-pretty">
          <span className="text-muted-foreground">GİRVAK’ın notu: </span>
          {not}
        </p>
      ))}
    </section>
  );
}

export function Degerlendirme({
  kimlik,
  not,
  incelemeBekliyor,
  kararaItiraz,
  bekleniyor,
  onItiraz,
}: {
  kimlik: string;
  not: string | null;
  incelemeBekliyor: boolean;
  kararaItiraz: boolean;
  bekleniyor: boolean;
  onItiraz: (aciklama: string) => Promise<boolean>;
}) {
  const [acik, setAcik] = useState(false);
  const [aciklama, setAciklama] = useState("");
  const notlar = notuBasliklaraAyir(not);

  return (
    <section className="flex flex-col gap-3 border-t border-kenar pt-4">
      {notlar.length > 0 ? (
        <div className="flex flex-col gap-2">
          <h4 className="text-sm font-semibold text-ana">
            Değerlendirme notları
          </h4>
          <ul className="flex flex-col gap-2">
            {notlar.map((parca, i) => (
              <li
                key={i}
                className="grid gap-x-3 gap-y-0.5 text-sm text-pretty sm:grid-cols-[5rem_1fr]"
              >
                <span className="font-medium text-metin">
                  {parca.baslik ?? "Genel"}
                </span>
                <span className="text-muted-foreground">{parca.metin}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {incelemeBekliyor ? (
        // İtiraz hakkı doldu; son itiraz GİRVAK'ta (docs/dogrulama.md § 9). Karar bildirimle gelir.
        <p className="text-sm text-muted-foreground text-pretty" role="status">
          İtirazın GİRVAK’a iletildi; inceleyip sonucu sana bildirecek. Yeni bir
          kanıt eklersen çalışman yeniden değerlendirilir.
        </p>
      ) : acik ? (
        <form
          className="flex flex-col gap-3"
          onSubmit={(olay) => {
            olay.preventDefault();
            if (aciklama.trim().length < 3) return;
            void onItiraz(aciklama.trim()).then((tamam) => {
              if (tamam) {
                setAciklama("");
                setAcik(false);
              }
            });
          }}
        >
          <FormAlani etiket="İtiraz nedeni" htmlFor={`itiraz-${kimlik}`}>
            <Input
              id={`itiraz-${kimlik}`}
              value={aciklama}
              onChange={(olay) => setAciklama(olay.target.value)}
              placeholder="ör. rolüm açıklamada net yazmıyordu"
            />
          </FormAlani>
          <p className="text-xs text-muted-foreground">
            {kararaItiraz
              ? "Neyin gözden kaçtığını yaz; itirazın GİRVAK’a gider ve sonucu sana bildirilir."
              : "Neyin gözden kaçtığını yaz; yeni bir kanıtın varsa yukarıdan ekle. Güven göstergesi yeniden hesaplanır, referans yanıtı korunur."}
          </p>
          <div className="flex flex-wrap gap-3">
            <Button
              type="submit"
              size="sm"
              disabled={bekleniyor || aciklama.trim().length < 3}
            >
              {bekleniyor ? "Yeniden bakılıyor…" : "İtirazı gönder"}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setAcik(false)}
            >
              Vazgeç
            </Button>
          </div>
        </form>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setAcik(true)}
          >
            {kararaItiraz ? "Karara itiraz et" : "Değerlendirmeye itiraz et"}
          </Button>
          <span className="text-xs text-muted-foreground">
            {kararaItiraz
              ? "GİRVAK’ın yeniden bakmasını isteyebilirsin."
              : "Değerlendirmeyi eksik buluyorsan yeniden bakılmasını isteyebilirsin."}
          </span>
        </div>
      )}
    </section>
  );
}
