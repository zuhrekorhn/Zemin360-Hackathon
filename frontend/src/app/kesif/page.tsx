"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import { KayitliKart } from "@/components/kesif/kayitli-kart";
import { TaslakBolumu } from "@/components/kesif/taslak-bolumu";
import { useKesifSohbeti } from "@/components/kesif/use-kesif-sohbeti";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { CevapAlani, HataKutusu, Sohbet } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { kartYolu } from "@/lib/yonlendirme";

/**
 * Keşif Ajanı sohbeti (docs/agent-specs.md § 1).
 *
 * Akış: sohbet → taslak gözden geçirme → onay formu → kaydedilen kart
 * (durum makinesi: components/kesif/use-kesif-sohbeti.ts). Kayıttan hemen
 * sonra buraya gelinir (`?ilk=1`, docs/plans/genc-akisi.md § 5.2); "Şimdilik
 * atla" panele götürür, kartı olmayan genç eşleştirmeye girmez ve panel onu
 * kart tamamlamaya çağırır. Kayıt formundaki bilgiler sohbette sorulmaz.
 *
 * Görsel dil (docs/design-language.md): sohbet balonları yuvarlak/sıcak,
 * taslak ve kayıtlı kart hairline çizgili ve az yuvarlak — "resmi belge".
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
 * Gencin tek kartı var (madde 7): kartı olan genç sohbet yerine kartına
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
  const sohbet = useKesifSohbeti();
  const [girdi, setGirdi] = useState("");
  const sonMesaj = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    sonMesaj.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [sohbet.mesajlar, sohbet.bekleniyor]);

  function gonder() {
    if (!girdi.trim() || sohbet.bekleniyor) return;
    sohbet.gonder(girdi);
    setGirdi("");
  }

  return (
    <Sayfa>
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
      >
        {ilkKez && sohbet.asama !== "kaydedildi" ? (
          <p className="text-sm text-pretty text-muted-foreground">
            Şimdi vaktin yoksa sonra da yapabilirsin; ama kartın olmadan
            firmalar seni göremez.{" "}
            <Link href="/genc" className="text-baglanti underline">
              Şimdilik atla
            </Link>
          </p>
        ) : null}
      </SayfaBasligi>

      {sohbet.asama === "sohbet" || sohbet.asama === "baslatiliyor" ? (
        <Sohbet
          ajanAdi="Zemin360"
          mesajlar={sohbet.mesajlar}
          bekleniyor={sohbet.bekleniyor}
          sonMesajRef={sonMesaj}
        />
      ) : null}

      {sohbet.hata ? (
        <HataKutusu hata={sohbet.hata} tekrarDene={sohbet.tekrarDene} />
      ) : null}

      {sohbet.asama === "sohbet" ? (
        <CevapAlani
          girdi={girdi}
          setGirdi={setGirdi}
          bekleniyor={sohbet.bekleniyor}
          gonder={gonder}
        />
      ) : null}

      {sohbet.asama === "taslak" && sohbet.taslak ? (
        <TaslakBolumu
          taslak={sohbet.taslak}
          bekleniyor={sohbet.bekleniyor}
          onOnayla={(profil, duzeltilmisTaslak) =>
            void sohbet.onayla(profil, duzeltilmisTaslak)
          }
        />
      ) : null}

      {sohbet.asama === "kaydedildi" && sohbet.kart ? (
        <KayitliKart kart={sohbet.kart} onGuncelle={sohbet.setKart} />
      ) : null}

      <footer className="mt-auto border-t border-kenar pt-6">
        <Button asChild variant="outline" size="lg">
          <Link href="/genc">Panele dön</Link>
        </Button>
      </footer>
    </Sayfa>
  );
}
