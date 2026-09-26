"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { GirisKapisi } from "@/components/giris-kapisi";
import { BosDurum, tarihYaz } from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import {
  type Bildirim,
  bildirimOkundu,
  bildirimler,
  hepsiniOku,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { useOturum } from "@/lib/oturum";
import { bildirimHedefi } from "@/lib/yonlendirme";

/**
 * Bildirimler (docs/faz-b-kimlik-ve-dongu.md § 6): en yeni önce. Bildirime
 * tıklamak onu okundu sayar ve ilgili yere götürür; "Hepsini okundu say"
 * menüdeki rozeti sıfırlar. Gerçek e-posta yok.
 */

export default function BildirimlerSayfasi() {
  return (
    <GirisKapisi>
      <BildirimListesi />
    </GirisKapisi>
  );
}

function BildirimListesi() {
  const router = useRouter();
  const { tazele } = useOturum();
  const [liste, setListe] = useState<Bildirim[] | null>(null);
  const [hata, setHata] = useState<Hata | null>(null);
  const [bekleniyor, setBekleniyor] = useState(false);
  const okundu = useRef(false);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      setListe(await bildirimler());
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, []);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku();
  }, [oku]);

  async function ac(bildirim: Bildirim) {
    try {
      if (!bildirim.okundu_tarihi) await bildirimOkundu(bildirim.id);
    } catch {
      // Okundu işaretlenemese de kullanıcı gitmek istediği yere gitsin.
    }
    router.push(bildirimHedefi(bildirim.tur));
  }

  async function hepsiniOkunduSay() {
    setHata(null);
    setBekleniyor(true);
    try {
      await hepsiniOku();
      const simdi = new Date().toISOString();
      setListe((oncekiler) =>
        (oncekiler ?? []).map((b) => ({
          ...b,
          okundu_tarihi: b.okundu_tarihi ?? simdi,
        })),
      );
      void tazele();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setBekleniyor(false);
    }
  }

  const okunmamis = liste?.filter((b) => !b.okundu_tarihi).length ?? 0;

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-2">
          <h1 className="font-heading text-2xl font-semibold text-ana sm:text-3xl">
            Bildirimler
          </h1>
          <p className="text-sm text-muted-foreground">
            {okunmamis > 0
              ? `${okunmamis} okunmamış bildirim.`
              : "Okunmamış bildirim yok."}
          </p>
        </div>
        {okunmamis > 0 ? (
          <Button
            type="button"
            variant="outline"
            size="lg"
            disabled={bekleniyor}
            onClick={() => void hepsiniOkunduSay()}
          >
            Hepsini okundu say
          </Button>
        ) : null}
      </header>

      {hata ? <HataKutusu hata={hata} tekrarDene={() => void oku()} /> : null}

      {liste === null ? (
        <p className="text-sm text-muted-foreground" role="status">
          Yükleniyor…
        </p>
      ) : liste.length === 0 ? (
        <BosDurum metin="Henüz bildirimin yok. Bir kurum kartınla ilgilendiğinde, bir genç ilgini yanıtladığında ya da yeni öneri çıktığında burada görünür." />
      ) : (
        <ul className="flex flex-col divide-y divide-kenar rounded-sm border border-kenar">
          {liste.map((bildirim) => (
            <li key={bildirim.id}>
              <button
                type="button"
                onClick={() => void ac(bildirim)}
                className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-muted"
              >
                <span
                  aria-hidden="true"
                  className={
                    bildirim.okundu_tarihi
                      ? "mt-1.5 size-2 shrink-0 rounded-full"
                      : "mt-1.5 size-2 shrink-0 rounded-full bg-vurgu"
                  }
                />
                <span className="flex flex-1 flex-col gap-0.5">
                  <span
                    className={
                      bildirim.okundu_tarihi
                        ? "text-sm text-pretty text-muted-foreground"
                        : "text-sm font-medium text-pretty"
                    }
                  >
                    {bildirim.metin}
                    {bildirim.okundu_tarihi ? null : (
                      <span className="sr-only"> (okunmadı)</span>
                    )}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {tarihYaz(bildirim.olusturma_tarihi, true)}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
