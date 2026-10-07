"use client";

import { ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";

import { EylemMenusu } from "@/components/eylem-menusu";
import { type EklemeFormu, KanitBolumu } from "@/components/kanit";
import { GuvenGostergesi } from "@/components/kart";
import {
  IsKalemiDuzenleFormu,
  IsKalemiSilmeOnayi,
} from "@/components/kart-duzenleme";
import { Button } from "@/components/ui/button";
import type {
  KanitDurumu,
  SomutCiktiYaniti,
  YetenekKartiYaniti,
} from "@/lib/api";
import { siradakiAdim } from "@/lib/calisma";
import { gostergeDoluMu } from "@/lib/guven-gostergesi";
import type { Hata } from "@/lib/hata";
import { IS_TURU_ETIKETLERI, etiketle } from "@/lib/sabitler";
import { cn } from "@/lib/utils";

/**
 * Gencin kendi kart sayfasında bir çalışma (docs/dogrulama.md § 1, § 3).
 *
 * Kapalıyken: çalışmanın özeti, dört başlıklı gösterge ve tek bir "sıradaki
 * adım". Kanıt ve referans listeleri, ekleme formları ve değerlendirme notları
 * "Kanıtlar ve referanslar" açılınca görünür; düzenleme ve silme "⋯"
 * menüsünde. Firma aynı çalışmayı `CiktiOzeti` ile salt okunur görür.
 */
export function CalismaKarti({
  kartId,
  cikti,
  durum,
  onDurum,
  onGuncel,
  onHata,
}: {
  kartId: string;
  cikti: SomutCiktiYaniti;
  durum: KanitDurumu | undefined;
  onDurum: (durum: KanitDurumu) => void;
  onGuncel: (kart: YetenekKartiYaniti, not?: string) => void;
  onHata: (hata: Hata | null) => void;
}) {
  const kimlik = `calisma-${cikti.id}`;
  // Ana sayfadaki "Kanıt ekle" bağlantısı bu çalışmaya gelir (#calisma-…):
  // ayrıntı açık ve link formu hazır gelsin. Sayfa giriş kapısından sonra
  // istemcide çizildiği için adres burada okunabilir.
  const [hedeflendi] = useState(
    () =>
      typeof window !== "undefined" && window.location.hash === `#${kimlik}`,
  );
  const [kip, setKip] = useState<"oku" | "duzenle" | "sil">("oku");
  const [ayrinti, setAyrinti] = useState(hedeflendi);
  const [acikForm, setAcikForm] = useState<EklemeFormu | null>(
    hedeflendi ? "link" : null,
  );

  useEffect(() => {
    if (hedeflendi)
      document.getElementById(kimlik)?.scrollIntoView({ block: "start" });
  }, [hedeflendi, kimlik]);

  const kanitSayisi = (durum?.kanitlar ?? cikti.kanitlar).length;
  const referansSayisi = durum?.referanslar.length ?? 0;
  const adim = siradakiAdim({
    kanitSayisi,
    referansSayisi,
    skor: cikti.guven_skoru,
  });

  function adimAt() {
    if (!adim) return;
    if (adim.tur === "sonuc" || adim.tur === "rol") {
      setKip("duzenle");
      return;
    }
    setAyrinti(true);
    setAcikForm(adim.tur === "referans" ? "referans" : "link");
  }

  const ozet = [
    kanitSayisi > 0 ? `${kanitSayisi} kanıt` : null,
    referansSayisi > 0 ? `${referansSayisi} referans` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <article
      id={kimlik}
      className="flex scroll-mt-24 flex-col rounded-md border border-kenar bg-card"
    >
      <div className="flex items-start justify-between gap-3 px-5 pt-4 pb-3">
        <div className="flex min-w-0 flex-col gap-1">
          <h3 className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[15px] leading-snug font-semibold text-metin">
            {cikti.baslik}
            {cikti.is_turu ? (
              <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-normal text-muted-foreground">
                {etiketle(IS_TURU_ETIKETLERI, cikti.is_turu)}
              </span>
            ) : null}
          </h3>
          {cikti.aciklama ? (
            <p
              className={cn(
                "text-sm text-pretty text-muted-foreground",
                !ayrinti && "line-clamp-2",
              )}
            >
              {cikti.aciklama}
            </p>
          ) : null}
        </div>
        <EylemMenusu
          etiket={`“${cikti.baslik}” için eylemler`}
          eylemler={[
            { etiket: "Düzenle", onSec: () => setKip("duzenle") },
            { etiket: "Sil", onSec: () => setKip("sil"), yikici: true },
          ]}
        />
      </div>

      {kip === "duzenle" ? (
        <div className="border-t border-kenar px-5 py-4">
          <IsKalemiDuzenleFormu
            kartId={kartId}
            cikti={cikti}
            onGuncel={onGuncel}
            onHata={onHata}
            onKapat={() => setKip("oku")}
          />
        </div>
      ) : kip === "sil" ? (
        <div className="px-5 pb-4">
          <IsKalemiSilmeOnayi
            kartId={kartId}
            cikti={cikti}
            onGuncel={onGuncel}
            onHata={onHata}
            onKapat={() => setKip("oku")}
          />
        </div>
      ) : cikti.olculebilir_sonuc || cikti.kendi_rolu ? (
        <dl className="flex flex-col gap-1 px-5 pb-3 text-sm">
          {cikti.olculebilir_sonuc ? (
            <div className="flex gap-2">
              <dt className="shrink-0 font-medium text-metin">Sonuç:</dt>
              <dd className="text-pretty">{cikti.olculebilir_sonuc}</dd>
            </div>
          ) : null}
          {cikti.kendi_rolu ? (
            <div className="flex gap-2">
              <dt className="shrink-0 font-medium text-metin">Payın:</dt>
              <dd className="text-pretty">{cikti.kendi_rolu}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}

      {cikti.guven_skoru && gostergeDoluMu(cikti.guven_skoru) ? (
        <GuvenGostergesi skor={cikti.guven_skoru} />
      ) : (
        <p className="border-t border-kenar px-5 py-3 text-sm text-muted-foreground">
          Henüz değerlendirilmedi. Kanıt ya da referans eklediğinde güven
          göstergesi burada görünür.
        </p>
      )}

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-kenar px-5 py-3">
        {adim && kip === "oku" ? (
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-2">
            <p className="min-w-0 flex-1 basis-56 text-sm text-pretty">
              <span className="font-medium text-ana">Sıradaki adım: </span>
              {adim.metin}
            </p>
            <Button type="button" size="sm" onClick={adimAt}>
              {adim.etiket}
            </Button>
          </div>
        ) : (
          <span className="flex-1" />
        )}
        <button
          type="button"
          aria-expanded={ayrinti}
          aria-controls={`${kimlik}-ayrinti`}
          onClick={() => setAyrinti((onceki) => !onceki)}
          className="ml-auto inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-muted-foreground outline-none hover:bg-muted hover:text-metin focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          Kanıtlar ve referanslar
          {ozet ? <span className="text-xs">({ozet})</span> : null}
          <ChevronDown
            aria-hidden="true"
            className={cn(
              "size-4 transition-transform",
              ayrinti && "rotate-180",
            )}
          />
        </button>
      </div>

      {ayrinti ? (
        <div
          id={`${kimlik}-ayrinti`}
          className="border-t border-kenar px-5 py-4"
        >
          <KanitBolumu
            somutCiktiId={cikti.id}
            kanitlar={cikti.kanitlar}
            durum={durum}
            onDurum={onDurum}
            onHata={onHata}
            acikForm={acikForm}
            onAcikForm={setAcikForm}
          />
        </div>
      ) : null}
    </article>
  );
}
