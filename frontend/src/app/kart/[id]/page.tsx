"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { BelgeKarti, CiktiOzeti, EtiketSatiri } from "@/components/kart";
import { KanitBolumu } from "@/components/kanit";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import {
  type KanitDurumu,
  type YetenekKartiYaniti,
  kanitDurumu,
  yetenekKartiGetir,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";

/**
 * Yetenek kartı + Doğrulama Ajanı ekranı (docs/agent-specs.md § 1 ve § 4).
 *
 * Kartın kendisi Keşif'te oluşuyor; burada her somut çıktıya kanıt ve
 * referans eklenip dört bileşenli güven göstergesi okunuyor. Kart sahibinin
 * e-postası hiçbir yerde gösterilmiyor (§ 1.5).
 */

export default function KartSayfasi() {
  const parametreler = useParams<{ id: string }>();
  const kartId = parametreler.id;

  const [kart, setKart] = useState<YetenekKartiYaniti | null>(null);
  // Çıktı başına kanıt durumu: referans listesi ve zaman aşımı yalnızca
  // /dogrulama/kanit/{id} yanıtında var (kart görünümü rubriği taşıyor,
  // referansları taşımıyor).
  const [kanitlar, setKanitlar] = useState<Record<string, KanitDurumu>>({});
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  const kartiGetir = useCallback(async (kimlik: string) => {
    setHata(null);
    setYukleniyor(true);
    try {
      const gelen = await yetenekKartiGetir(kimlik);
      setKart(gelen);

      // Zaman aşımı (bekliyor → yanit_yok) bu okuma anında hesaplanıyor;
      // ayrı bir zamanlayıcı yok (bilinçli, bkz. CLAUDE.md).
      const durumlar = await Promise.all(
        gelen.somut_ciktilar.map((cikti) => kanitDurumu(cikti.id)),
      );
      setKanitlar(
        Object.fromEntries(
          durumlar.map((durum) => [durum.somut_cikti_id, durum]),
        ),
      );
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setYukleniyor(false);
    }
  }, []);

  useEffect(() => {
    if (okundu.current || !kartId) return;
    okundu.current = true;
    void kartiGetir(kartId);
  }, [kartId, kartiGetir]);

  function kanidiGuncelle(durum: KanitDurumu) {
    setKanitlar((oncekiler) => ({
      ...oncekiler,
      [durum.somut_cikti_id]: durum,
    }));
    // Rubrik kart görünümünde de duruyor; iki yerde farklı puan görünmesin.
    setKart((onceki) =>
      onceki
        ? {
            ...onceki,
            somut_ciktilar: onceki.somut_ciktilar.map((cikti) =>
              cikti.id === durum.somut_cikti_id
                ? {
                    ...cikti,
                    kanit_linki: durum.kanit_linki,
                    guven_skoru: durum.guven_skoru,
                  }
                : cikti,
            ),
          }
        : onceki,
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-col gap-2">
        <h1 className="font-heading text-2xl font-semibold text-ana sm:text-3xl">
          Yetenek kartın
        </h1>
        <p className="text-sm text-pretty text-muted-foreground">
          Her somut çıktıya kanıt ekleyip referans isteyebilirsin. Doğrulama
          Ajanı kanıtı dört ayrı başlıkta puanlar — tek bir “güven puanı”na
          indirmez.
        </p>
      </header>

      {hata ? (
        <HataKutusu
          hata={hata}
          tekrarDene={() => {
            if (kartId) void kartiGetir(kartId);
          }}
        />
      ) : null}

      {yukleniyor ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <span
            aria-hidden="true"
            className="size-2 rounded-full bg-baglanti motion-safe:animate-pulse"
          />
          Kart okunuyor…
        </p>
      ) : null}

      {!yukleniyor && kart ? (
        <>
          <BelgeKarti
            baslik={kart.rol_alani}
            altbaslik={`Deneyim: ${kart.deneyim_seviyesi}`}
            rozet={
              kart.kanit_bekleyen ? (
                <span className="rounded-sm border border-kenar px-2.5 py-1 text-xs text-muted-foreground">
                  Kanıt bekliyor
                </span>
              ) : null
            }
          >
            <EtiketSatiri
              etiket="Araçlar"
              degerler={kart.araclar_teknolojiler}
            />
            <EtiketSatiri
              etiket="Sektör ilgisi"
              degerler={kart.sektor_ilgi_alani}
            />
            <p className="text-xs text-muted-foreground">
              Bu görünüm iletişim bilgisi taşımaz; kurumlar kartı böyle görür.
            </p>
          </BelgeKarti>

          <section className="flex flex-col gap-6">
            <h2 className="font-heading text-xl font-semibold text-ana">
              Somut çıktılar
            </h2>

            {kart.somut_ciktilar.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Bu kartta somut çıktı yok. Keşif sohbetinde ekleyebilirsin.
              </p>
            ) : (
              kart.somut_ciktilar.map((cikti) => (
                <div key={cikti.id} className="flex flex-col gap-3">
                  <CiktiOzeti cikti={cikti} />
                  <KanitBolumu
                    somutCiktiId={cikti.id}
                    durum={kanitlar[cikti.id]}
                    onDurum={kanidiGuncelle}
                    onHata={setHata}
                  />
                </div>
              ))
            )}
          </section>
        </>
      ) : null}

      <footer className="mt-auto flex flex-wrap gap-3 border-t border-kenar pt-6">
        <Button asChild variant="outline" size="lg">
          <Link href="/">Ana sayfaya dön</Link>
        </Button>
      </footer>
    </main>
  );
}
