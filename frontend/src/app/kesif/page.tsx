"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import { CanliOnizleme } from "@/components/kesif/canli-onizleme";
import { KayitliKart } from "@/components/kesif/kayitli-kart";
import { TaslakBolumu } from "@/components/kesif/taslak-bolumu";
import { useKesifSohbeti } from "@/components/kesif/use-kesif-sohbeti";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { CevapAlani, HataKutusu, Sohbet } from "@/components/sohbet";
import { adGosterimi } from "@/lib/ad";
import { kartYolu } from "@/lib/yonlendirme";

/**
 * Keşif Ajanı sohbeti (docs/agent-specs.md § 1).
 *
 * Akış: sohbet → taslak gözden geçirme → onay formu → kaydedilen kart
 * (durum makinesi: components/kesif/use-kesif-sohbeti.ts). Kayıttan hemen
 * sonra buraya gelinir (`?ilk=1`, docs/agent-specs.md § 1); "Şimdilik
 * atla" panele götürür, kartı olmayan genç eşleştirmeye girmez ve panel onu
 * kart tamamlamaya çağırır. Kayıt formundaki bilgiler sohbette sorulmaz.
 *
 * Sohbet sürerken sağda kartın canlı hali (components/kesif/canli-onizleme.tsx):
 * backend her turda taslağı döndürüyor; genç neyin sorulacağını ve ne kadar
 * kaldığını görür. Görsel dil (docs/design-language.md): sohbet balonları
 * yuvarlak/sıcak, kart hairline çizgili — "resmi belge".
 */

export default function KesifSayfasi() {
  return (
    <Suspense fallback={null}>
      <GirisKapisi roller={["genc"]}>
        <KartiOlanaYonlendir>
          <KesifSohbeti />
        </KartiOlanaYonlendir>
      </GirisKapisi>
    </Suspense>
  );
}

/**
 * Gencin tek kartı var (docs/kararlar.md G17): kartı olan genç sohbet yerine kartına
 * gider. Karar sayfanın açıldığı anki duruma göre verilir: onaydan sonra
 * oturum tazelenince genç "Kartın kaydedildi" ekranından atılmasın.
 */
function KartiOlanaYonlendir({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { yetenek_karti } = useGirisliHesap();
  const [acilistakiKart] = useState(yetenek_karti);
  useEffect(() => {
    if (acilistakiKart) router.replace(kartYolu(acilistakiKart));
  }, [acilistakiKart, router]);
  return acilistakiKart ? null : children;
}

function KesifSohbeti() {
  // Kayıttan hemen sonra (onboarding): "Şimdilik atla" görünür.
  const ilkKez = useSearchParams().get("ilk") === "1";
  const hesap = useGirisliHesap();
  const sohbet = useKesifSohbeti();
  const [girdi, setGirdi] = useState("");
  const sonMesaj = useRef<HTMLDivElement | null>(null);
  const sohbetAsamasi =
    sohbet.asama === "sohbet" || sohbet.asama === "baslatiliyor";

  function gonder() {
    if (!girdi.trim() || sohbet.bekleniyor) return;
    sohbet.gonder(girdi);
    setGirdi("");
  }

  const baslik = (
    <SayfaBasligi
      baslik="Yetenek kartını oluştur"
      aciklama={
        <>
          Kısa bir sohbetle neler yaptığını birlikte bir yetenek kartına
          dönüştüreceğiz. Bu sohbet yapay zekâ desteğiyle ilerler. Kartın sen
          onaylamadan kaydedilmez.
          {ilkKez ? " Kayıtta verdiğin bilgileri tekrar sormayacağız." : null}
        </>
      }
      eylem={
        ilkKez && sohbet.asama !== "kaydedildi" ? (
          <Link
            href="/genc"
            className="text-sm text-muted-foreground underline underline-offset-4 hover:text-metin"
          >
            Şimdilik atla
          </Link>
        ) : null
      }
    />
  );

  // Sohbet sürerken: solda sohbet, sağda kartın canlı hali.
  if (sohbetAsamasi) {
    return (
      <Sayfa genislik="genis">
        <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="flex min-w-0 flex-col gap-6">
            {baslik}
            {sohbet.hata ? (
              <HataKutusu hata={sohbet.hata} tekrarDene={sohbet.tekrarDene} />
            ) : null}
            <Sohbet
              ajanAdi="Zemin360"
              mesajlar={sohbet.mesajlar}
              bekleniyor={sohbet.bekleniyor}
              sonMesajRef={sonMesaj}
              altKisim={
                sohbet.asama === "sohbet" ? (
                  <CevapAlani
                    girdi={girdi}
                    setGirdi={setGirdi}
                    bekleniyor={sohbet.bekleniyor}
                    gonder={gonder}
                  />
                ) : null
              }
            />
          </div>
          <aside aria-label="Kartın" className="lg:sticky lg:top-24">
            <CanliOnizleme
              taslak={sohbet.taslak}
              ad={adGosterimi(hesap.ad ?? "")}
            />
          </aside>
        </div>
      </Sayfa>
    );
  }

  if (sohbet.asama === "kaydedildi" && sohbet.kart) {
    return (
      <Sayfa genislik="genis">
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
          <h1 className="sr-only">Kartın kaydedildi</h1>
          <KayitliKart kart={sohbet.kart} onGuncelle={sohbet.setKart} />
        </div>
      </Sayfa>
    );
  }

  // Taslak: sohbetten çıkan kartı gözden geçirip onaylama.
  return (
    <Sayfa genislik="genis">
      <SayfaBasligi
        baslik="Kartını gözden geçir"
        aciklama="Sohbetten çıkan kart bu. Yanlış anlaşılan bir şey varsa düzelt; doğruysa onayla. Kartın sen onaylamadan kaydedilmez."
      />
      {sohbet.hata ? (
        <HataKutusu hata={sohbet.hata} tekrarDene={sohbet.tekrarDene} />
      ) : null}
      {sohbet.taslak ? (
        <TaslakBolumu
          taslak={sohbet.taslak}
          bekleniyor={sohbet.bekleniyor}
          onOnayla={(profil, duzeltilmisTaslak) =>
            void sohbet.onayla(profil, duzeltilmisTaslak)
          }
        />
      ) : null}
    </Sayfa>
  );
}
