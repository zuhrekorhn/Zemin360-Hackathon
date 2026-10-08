"use client";

import { ListeIskeleti } from "@/components/ui/iskelet";
import { ChevronRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
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

// Rehber § 3: gence "sen", firmaya ve GİRVAK'a "siz".
const BOS_METINLERI: Record<string, string> = {
  genc: "Henüz bildirimin yok. Bir firma kartınla ilgilendiğinde ya da sana uygun yeni bir fırsat çıktığında burada görünür.",
  kurum:
    "Henüz bildiriminiz yok. Bir aday ilginizi yanıtladığında ya da ihtiyacınıza yeni adaylar çıktığında burada görünür.",
  girvak: "Henüz bildiriminiz yok.",
};

/**
 * Bildirimler (docs/kimlik-ve-dongu.md § 6): en yeni önce. Bildirime
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
  const hesap = useGirisliHesap();
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
    router.push(
      bildirimHedefi(
        bildirim.tur,
        bildirim.isbirligi_id,
        hesap.rol,
        hesap.yetenek_karti,
      ),
    );
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
    <Sayfa>
      <SayfaBasligi
        baslik="Bildirimler"
        aciklama={
          okunmamis > 0
            ? `${okunmamis} okunmamış bildirim.`
            : "Okunmamış bildirim yok."
        }
        eylem={
          okunmamis > 0 ? (
            <Button
              type="button"
              variant="outline"
              size="lg"
              disabled={bekleniyor}
              onClick={() => void hepsiniOkunduSay()}
            >
              Hepsini okundu say
            </Button>
          ) : null
        }
      />

      {hata ? <HataKutusu hata={hata} tekrarDene={() => void oku()} /> : null}

      {liste === null ? (
        <ListeIskeleti />
      ) : liste.length === 0 ? (
        <BosDurum metin={BOS_METINLERI[hesap.rol] ?? BOS_METINLERI.girvak} />
      ) : (
        <ul className="flex flex-col divide-y divide-kenar overflow-hidden rounded-xl border border-kenar bg-card shadow-[0_1px_2px_rgb(22_33_27/0.05)]">
          {liste.map((bildirim) => (
            <li key={bildirim.id}>
              <button
                type="button"
                onClick={() => void ac(bildirim)}
                className={`group flex w-full items-start gap-3 border-l-[3px] px-5 py-4 text-left hover:bg-muted ${bildirim.okundu_tarihi ? "border-l-transparent" : "border-l-vurgu"}`}
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
                        ? "text-[15px] text-pretty text-muted-foreground"
                        : "text-[15px] font-medium text-pretty"
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
                <ChevronRight
                  aria-hidden="true"
                  className="mt-0.5 size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5"
                />
              </button>
            </li>
          ))}
        </ul>
      )}
    </Sayfa>
  );
}
