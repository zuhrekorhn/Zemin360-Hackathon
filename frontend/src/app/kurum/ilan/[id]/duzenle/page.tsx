"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { EslestirmeyeHazirla } from "@/components/eslestirmeye-hazirla";
import { GirisKapisi } from "@/components/giris-kapisi";
import { IhtiyacFormu } from "@/components/ihtiyac-formu";
import { Sayfa, SayfaBasligi, SayfaDurumu } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import {
  type IhtiyacKartiYaniti,
  ihtiyacKarti,
  ihtiyacKartiDuzenle,
  ihtiyacKartiHazirla,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";

/**
 * İlan düzenleme (docs/kararlar.md D1). Onaydaki formun aynısı;
 * kapı (genç / iş birliği ortağı) değişmez. Kapalı ya da iş birliği başlamış
 * ilanda backend 409 ve nedenini döner, o cümle gösterilir.
 */
export default function IlanDuzenlemeSayfasi() {
  return (
    <GirisKapisi roller={["kurum"]}>
      <IlanDuzenleme />
    </GirisKapisi>
  );
}

function IlanDuzenleme() {
  const { id } = useParams<{ id: string }>();
  const [kart, setKart] = useState<IhtiyacKartiYaniti | null>(null);
  const [kaydedildi, setKaydedildi] = useState(false);
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      setKart(await ihtiyacKarti(id));
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, [id]);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku();
  }, [oku]);

  if (!kart) {
    return (
      <SayfaDurumu genislik="form" hata={hata} tekrarDene={() => void oku()} />
    );
  }

  return (
    <Sayfa genislik="form">
      <SayfaBasligi
        baslik="İhtiyacı düzenleyin"
        aciklama="Yaptığınız değişiklikler kaydedildiği anda ihtiyacınızda görünür."
      />

      {hata ? <HataKutusu hata={hata} /> : null}

      {kaydedildi ? (
        <section className="flex flex-col gap-3">
          <h2 className="font-heading text-xl font-semibold text-ana">
            Değişiklikleriniz kaydedildi
          </h2>
          {kart.embedding_var ? (
            <p className="text-sm text-pretty text-muted-foreground">
              Uygun adaylar yeniden belirleniyor.
            </p>
          ) : (
            <EslestirmeyeHazirla
              hazirla={async () => setKart(await ihtiyacKartiHazirla(kart.id))}
            />
          )}
          <Button asChild size="lg" className="mt-1 w-fit">
            <Link href={`/kurum/oneriler?ihtiyac=${kart.id}`}>
              Uygun adayları gör
            </Link>
          </Button>
        </section>
      ) : (
        <IhtiyacFormu
          taslak={kart}
          ortak={kart.aranan === "firma"}
          bekleniyor={bekleniyor}
          duzenleme
          onGonder={async (_kurumProfili, taslak) => {
            setHata(null);
            setBekleniyor(true);
            try {
              setKart(await ihtiyacKartiDuzenle(kart.id, taslak));
              setKaydedildi(true);
            } catch (sebep) {
              setHata(hatayaCevir(sebep));
            } finally {
              setBekleniyor(false);
            }
          }}
        />
      )}

      <footer className="mt-auto border-t border-kenar pt-6">
        <Button asChild variant="outline" size="lg">
          <Link href="/kurum">Panele dön</Link>
        </Button>
      </footer>
    </Sayfa>
  );
}
