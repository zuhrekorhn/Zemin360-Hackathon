"use client";

import { ListeIskeleti } from "@/components/ui/iskelet";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { EslestirmeyeHazirla } from "@/components/eslestirmeye-hazirla";
import { IhtiyacFormu } from "@/components/ihtiyac-formu";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { YanPanel } from "@/components/ui/yan-panel";
import {
  type IhtiyacKartiYaniti,
  ihtiyacKarti,
  ihtiyacKartiDuzenle,
  ihtiyacKartiHazirla,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";

const FORM_KIMLIGI = "ilan-duzenleme-formu";

/**
 * İhtiyaç düzenleme (docs/kararlar.md D1): firma panelinde sağdan açılan panel,
 * gencin "Kartı düzenle" paneliyle aynı kalıp. Onaydaki formun aynısı; kapı
 * (genç / iş birliği ortağı) değişmez. Kapalı ya da iş birliği başlamış
 * ilanda backend 409 ve nedenini döner, o cümle gösterilir.
 *
 * Panel her açılışta yeniden kurulur (`key={kartId}`): kart sunucudan taze okunur.
 */
export function IlanDuzenlemePaneli({
  kartId,
  onKapat,
  onKaydedildi,
}: {
  kartId: string;
  onKapat: () => void;
  /** Kayıttan sonra panel verisini (ihtiyaç listesi, adaylar) tazelemek için. */
  onKaydedildi: () => void;
}) {
  const [kart, setKart] = useState<IhtiyacKartiYaniti | null>(null);
  const [kaydedildi, setKaydedildi] = useState(false);
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      setKart(await ihtiyacKarti(kartId));
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, [kartId]);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku();
  }, [oku]);

  return (
    <YanPanel
      acik
      onKapat={onKapat}
      ust="İhtiyacı düzenleyin"
      baslik="İhtiyaç kartınız"
      alt={
        kaydedildi
          ? undefined
          : "Değiştirmek istediğiniz alanları düzeltin, sonra kaydedin."
      }
      etek={
        kaydedildi && kart ? (
          <>
            <Button asChild size="lg">
              <Link href={`/kurum/oneriler?ihtiyac=${kart.id}`}>
                Uygun adayları gör
              </Link>
            </Button>
            <Button type="button" size="lg" variant="ghost" onClick={onKapat}>
              Kapat
            </Button>
          </>
        ) : kart ? (
          <>
            <Button
              type="submit"
              form={FORM_KIMLIGI}
              size="lg"
              disabled={bekleniyor}
            >
              {bekleniyor ? "Kaydediliyor…" : "Değişiklikleri kaydet"}
            </Button>
            <Button
              type="button"
              size="lg"
              variant="ghost"
              disabled={bekleniyor}
              onClick={onKapat}
            >
              Vazgeç
            </Button>
          </>
        ) : undefined
      }
    >
      {hata ? (
        <HataKutusu
          hata={hata}
          tekrarDene={kart ? undefined : () => void oku()}
        />
      ) : null}

      {!kart ? (
        hata ? null : (
          <ListeIskeleti satir={3} />
        )
      ) : kaydedildi ? (
        <section className="flex flex-col gap-3">
          <h3 className="font-heading text-lg font-semibold text-ana">
            Değişiklikleriniz kaydedildi
          </h3>
          {kart.embedding_var ? (
            <p className="text-sm text-pretty text-muted-foreground">
              Uygun adaylar yeniden belirleniyor. İlgilendiğiniz ve size ilgi
              gösteren adaylar korunur.
            </p>
          ) : (
            <EslestirmeyeHazirla
              hazirla={async () => setKart(await ihtiyacKartiHazirla(kart.id))}
            />
          )}
        </section>
      ) : (
        <IhtiyacFormu
          taslak={kart}
          ortak={kart.aranan === "firma"}
          bekleniyor={bekleniyor}
          duzenleme
          baslikGizle
          formId={FORM_KIMLIGI}
          onGonder={async (_kurumProfili, taslak) => {
            setHata(null);
            setBekleniyor(true);
            try {
              setKart(await ihtiyacKartiDuzenle(kart.id, taslak));
              setKaydedildi(true);
              onKaydedildi();
            } catch (sebep) {
              setHata(hatayaCevir(sebep));
            } finally {
              setBekleniyor(false);
            }
          }}
        />
      )}
    </YanPanel>
  );
}
