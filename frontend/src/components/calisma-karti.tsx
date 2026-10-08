"use client";

import { AlertCircle, CheckCircle2, ExternalLink } from "lucide-react";
import { useState } from "react";

import { GostergeKarolari } from "@/components/kart";
import {
  IsKalemiDuzenleFormu,
  IsKalemiSilmeOnayi,
} from "@/components/kart-duzenleme";
import { Button } from "@/components/ui/button";
import { YanPanel } from "@/components/ui/yan-panel";
import { DIKKAT, KUTU } from "@/components/ui/yuzey";
import type {
  KanitDurumu,
  SomutCiktiYaniti,
  YetenekKartiYaniti,
} from "@/lib/api";
import { eksikler } from "@/lib/calisma";
import { gostergeDoluMu, notuBasliklaraAyir } from "@/lib/guven-gostergesi";
import type { Hata } from "@/lib/hata";
import { kanitAdresi, kanitLinkleri } from "@/lib/kanit";
import { IS_TURU_ETIKETLERI, etiketle } from "@/lib/sabitler";
import { cn } from "@/lib/utils";

/**
 * Gencin kendi kart sayfasında bir çalışma (docs/dogrulama.md § 1, docs/kararlar.md G18).
 *
 * Özet, kanıt linki, dört gösterge karosu (zayıf olan amber) ve kanıt
 * çalışmayı göstermiyorsa kartın içinde uyarı. Altta kaç eksik kaldığı ve en
 * hızlısı; bütün eksikler "Güçlendir" panelinde adım adım. Düzenleme
 * yerinde açılır, silme düzenleme formunun içinde. Firma aynı çalışmayı
 * `CiktiOzeti` ile salt okunur görür.
 */
export function CalismaKarti({
  kartId,
  cikti,
  durum,
  onGuclendir,
  onGuncel,
  onHata,
}: {
  kartId: string;
  cikti: SomutCiktiYaniti;
  durum: KanitDurumu | undefined;
  onGuclendir: () => void;
  onGuncel: (kart: YetenekKartiYaniti, not?: string) => void;
  onHata: (hata: Hata | null) => void;
}) {
  const [kip, setKip] = useState<"oku" | "duzenle" | "sil">("oku");
  const parcalar = durum?.kanitlar ?? cikti.kanitlar;
  const ilkLink = kanitLinkleri(parcalar)[0];
  const skor = durum?.guven_skoru ?? cikti.guven_skoru;
  const liste = eksikler({
    kanitSayisi: parcalar.length,
    referansSayisi: durum?.referanslar.length ?? 0,
    skor,
  });
  // Kanıt var ama çalışmayı göstermiyor: değerlendirmenin cümlesi kartın içinde.
  const kanitUyarisi =
    liste[0]?.tur === "kanit" && parcalar.length > 0
      ? (notuBasliklaraAyir(skor?.gerekce_metni).find(
          (p) => p.baslik === "Kanıt",
        )?.metin ?? liste[0].metin)
      : null;

  return (
    <article
      id={`calisma-${cikti.id}`}
      className={cn(KUTU, "flex scroll-mt-24 flex-col gap-4 px-5 py-5")}
    >
      <header className="flex flex-col gap-1.5">
        <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
          <h3 className="flex flex-wrap items-center gap-2 text-base leading-snug font-semibold text-metin">
            {cikti.baslik}
            {cikti.is_turu ? (
              <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-normal text-muted-foreground">
                {etiketle(IS_TURU_ETIKETLERI, cikti.is_turu)}
              </span>
            ) : null}
          </h3>
          {ilkLink ? (
            <a
              href={kanitAdresi(ilkLink.url)}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex max-w-64 items-center gap-1 text-sm text-baglanti underline-offset-4 hover:underline"
            >
              <ExternalLink aria-hidden="true" className="size-3.5 shrink-0" />
              <span className="truncate">
                {ilkLink.url.replace(/^https?:\/\/(www\.)?/, "")}
              </span>
            </a>
          ) : null}
        </div>
        {cikti.aciklama ? (
          <p className="line-clamp-2 max-w-prose text-sm text-pretty text-muted-foreground">
            {cikti.aciklama}
          </p>
        ) : null}
        {cikti.kendi_rolu ? (
          <p className="text-sm text-pretty">
            <span className="font-medium">Payın: </span>
            {cikti.kendi_rolu}
          </p>
        ) : null}
        {cikti.olculebilir_sonuc ? (
          <p className="text-sm text-pretty">
            <span className="font-medium">Sonuç: </span>
            {cikti.olculebilir_sonuc}
          </p>
        ) : null}
      </header>

      <YanPanel
        acik={kip === "duzenle"}
        onKapat={() => setKip("oku")}
        ust="Çalışmayı düzenle"
        baslik={cikti.baslik}
        alt="Kanıt ve referanslar Güçlendir'de."
      >
        <IsKalemiDuzenleFormu
          kartId={kartId}
          cikti={cikti}
          onGuncel={onGuncel}
          onHata={onHata}
          onKapat={() => setKip("oku")}
          onSil={() => setKip("sil")}
        />
      </YanPanel>

      {kip === "sil" ? (
        <IsKalemiSilmeOnayi
          kartId={kartId}
          cikti={cikti}
          onGuncel={onGuncel}
          onHata={onHata}
          onKapat={() => setKip("oku")}
        />
      ) : (
        <>
          {kanitUyarisi ? (
            <p
              className={cn(
                DIKKAT,
                "flex items-start gap-2 rounded-lg px-3 py-2.5 text-sm text-pretty",
              )}
            >
              <AlertCircle
                aria-hidden="true"
                className="mt-0.5 size-4 shrink-0 text-vurgu"
              />
              {kanitUyarisi}
            </p>
          ) : null}

          {skor && gostergeDoluMu(skor) ? (
            <GostergeKarolari skor={skor} />
          ) : (
            <p className="rounded-lg bg-zemin px-3 py-2.5 text-sm text-muted-foreground">
              Henüz değerlendirilmedi. Kanıt ya da referans eklediğinde güven
              göstergesi burada görünür.
            </p>
          )}

          <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-kenar pt-4">
            <p className="text-sm text-pretty">
              {liste.length === 0 ? (
                skor ? (
                  <span className="inline-flex items-center gap-1.5 text-baglanti">
                    <CheckCircle2 aria-hidden="true" className="size-4" />
                    Eksik yok
                  </span>
                ) : (
                  <span className="text-muted-foreground">
                    Değerlendirme bekleniyor
                  </span>
                )
              ) : liste.length === 1 ? (
                <>
                  <span className="text-muted-foreground">1 eksik: </span>
                  <span className="font-semibold">{liste[0].kisa}</span>
                </>
              ) : (
                <>
                  <span className="text-muted-foreground">
                    {liste.length} eksik · en hızlısı:{" "}
                  </span>
                  <span className="font-semibold">{liste[0].kisa}</span>
                </>
              )}
            </p>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setKip("duzenle")}
              >
                Düzenle
              </Button>
              <Button
                type="button"
                variant={liste.length > 0 ? "default" : "outline"}
                size="lg"
                className="px-4"
                onClick={onGuclendir}
              >
                {liste.length > 0 ? "Güçlendir" : "Kanıt ve referanslar"}
              </Button>
            </div>
          </footer>
        </>
      )}
    </article>
  );
}
