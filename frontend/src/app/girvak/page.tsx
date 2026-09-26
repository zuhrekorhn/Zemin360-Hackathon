"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { GirisKapisi } from "@/components/giris-kapisi";
import { PanelBolumu } from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { type GirvakSayilari, girvakSayilari } from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";

/**
 * GİRVAK paneli (docs/faz-b-kimlik-ve-dongu.md § 7). Faz B'de yalnızca
 * sayılar: hesap, kart, eşleşme, iş birliği. Hedefler ve grafikler Faz D'de
 * bu sayfaya eklenecek; "yakında" diyen boş bir ekran yok.
 */

export default function GirvakPaneli() {
  return (
    <GirisKapisi roller={["girvak"]}>
      <GirvakSayfasi />
    </GirisKapisi>
  );
}

function GirvakSayfasi() {
  const [sayilar, setSayilar] = useState<GirvakSayilari | null>(null);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      setSayilar(await girvakSayilari());
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, []);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku();
  }, [oku]);

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-col gap-2">
        <h1 className="font-heading text-2xl font-semibold text-ana sm:text-3xl">
          Platform sayıları
        </h1>
        <p className="text-sm text-pretty text-muted-foreground">
          Hesaplar, kartlar ve döngünün her aşamasındaki eşleşmeler. Kişisel
          bilgi yok, yalnızca sayım.
        </p>
      </header>

      {hata ? <HataKutusu hata={hata} tekrarDene={() => void oku()} /> : null}

      {sayilar === null && !hata ? (
        <p className="text-sm text-muted-foreground" role="status">
          Yükleniyor…
        </p>
      ) : null}

      {sayilar ? (
        <>
          <PanelBolumu baslik="Hesaplar ve kartlar">
            <SayiIzgarasi
              ogeler={[
                { etiket: "Genç hesabı", sayi: sayilar.hesap.genc },
                { etiket: "Kurum hesabı", sayi: sayilar.hesap.kurum },
                { etiket: "Yetenek kartı", sayi: sayilar.yetenek_karti },
                { etiket: "İhtiyaç kartı", sayi: sayilar.ihtiyac_karti },
              ]}
            />
          </PanelBolumu>

          <PanelBolumu
            baslik="Eşleşmeler ve iş birlikleri"
            aciklama="Öneriden iş birliğine: kurum ilgilenir, genç kabul eder ya da etmez."
          >
            <SayiIzgarasi
              ogeler={[
                { etiket: "Önerildi", sayi: sayilar.eslesme.onerildi },
                {
                  etiket: "Gencin yanıtı bekleniyor",
                  sayi: sayilar.eslesme.ilgileniliyor,
                },
                { etiket: "Kabul edildi", sayi: sayilar.eslesme.kabul_edildi },
                { etiket: "Reddedildi", sayi: sayilar.eslesme.reddedildi },
                { etiket: "İş birliği", sayi: sayilar.isbirligi },
              ]}
            />
          </PanelBolumu>
        </>
      ) : null}
    </main>
  );
}

/** Hairline ızgara — doğrulama göstergesiyle aynı "belge" dili. */
function SayiIzgarasi({
  ogeler,
}: {
  ogeler: { etiket: string; sayi: number }[];
}) {
  return (
    <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-sm border border-kenar bg-kenar sm:grid-cols-3">
      {ogeler.map((oge) => (
        <div key={oge.etiket} className="flex flex-col gap-1 bg-card px-4 py-3">
          <dt className="text-xs text-muted-foreground">{oge.etiket}</dt>
          <dd className="font-mono text-2xl text-ana">{oge.sayi}</dd>
        </div>
      ))}
    </dl>
  );
}
