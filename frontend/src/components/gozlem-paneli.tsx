"use client";

import { ListeIskeleti } from "@/components/ui/iskelet";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  BosDurum,
  DurumEtiketi,
  PanelBolumu,
  tarihYaz,
} from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { type GozlemYaniti, girvakGozlem } from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import {
  GOZLEM_GUNLERI,
  erisimEtiketi,
  platformEtiketi,
  servisEtiketi,
  servisOzeti,
  servisSayilari,
  sureYaz,
  yuzdeYaz,
} from "@/lib/gozlem";

/**
 * GİRVAK: gözlem (docs/dogrulama.md § 10.3).
 *
 * İki görünüm: kanıt linklerinin platform bazında açılma oranı ve dış
 * servislerin kalıcı durumu. Kayıtlar kişi ve adres taşımaz; 90 gün saklanır.
 */
export function GozlemPaneli() {
  const [gun, setGun] = useState<number>(30);
  const [veri, setVeri] = useState<GozlemYaniti | null>(null);
  const [hata, setHata] = useState<Hata | null>(null);
  const istek = useRef(0);
  const okundu = useRef(false);

  const oku = useCallback(async (g: number) => {
    const bu = ++istek.current;
    setHata(null);
    try {
      const yanit = await girvakGozlem(g);
      if (bu === istek.current) setVeri(yanit);
    } catch (sebep) {
      if (bu === istek.current) setHata(hatayaCevir(sebep));
    }
  }, []);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku(30);
  }, [oku]);

  function donemSec(g: number) {
    setGun(g);
    void oku(g);
  }

  return (
    <PanelBolumu
      id="gozlem"
      baslik="Gözlem"
      aciklama="Kanıt linklerinin ne kadarının açılabildiği ve dış servislerin durumu. Kayıtlarda kişi ya da adres bulunmaz; 90 gün saklanır."
    >
      <div
        className="flex flex-wrap items-center gap-2"
        role="group"
        aria-label="Dönem"
      >
        {GOZLEM_GUNLERI.map((g) => (
          <Button
            key={g}
            type="button"
            size="sm"
            variant={g === gun ? "default" : "outline"}
            aria-pressed={g === gun}
            onClick={() => donemSec(g)}
          >
            Son {g} gün
          </Button>
        ))}
      </div>

      {hata ? (
        <HataKutusu hata={hata} tekrarDene={() => void oku(gun)} />
      ) : null}

      {veri ? (
        <>
          <ErisimDagilimi veri={veri} />
          <Servisler veri={veri} />
          <DegerlendirmeOzeti veri={veri} />
        </>
      ) : hata ? null : (
        <ListeIskeleti satir={3} />
      )}
    </PanelBolumu>
  );
}

function ErisimDagilimi({ veri }: { veri: GozlemYaniti }) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-medium text-ana">Platform bazında erişim</h3>
      {veri.erisim.length === 0 ? (
        <BosDurum metin="Bu dönemde okunan kanıt linki yok." />
      ) : (
        <ul className="flex flex-col divide-y divide-kenar overflow-hidden rounded-xl border border-kenar">
          {veri.erisim.map((p) => {
            const digerleri = Object.entries(p.erisimler).filter(
              ([erisim, sayi]) => erisim !== "acik" && sayi > 0,
            );
            return (
              <li key={p.platform} className="flex flex-col gap-1.5 px-4 py-3">
                <div className="flex flex-wrap items-baseline justify-between gap-x-4">
                  <span className="text-sm font-medium text-ana">
                    {platformEtiketi(p.platform)}
                  </span>
                  <span className="font-mono text-sm text-ana">
                    {yuzdeYaz(p.acik_orani)} açık · {p.toplam} okuma
                  </span>
                </div>
                <div
                  className="h-1.5 w-full overflow-hidden rounded-full bg-kenar"
                  role="progressbar"
                  aria-valuenow={Math.round(p.acik_orani * 100)}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`${platformEtiketi(p.platform)} açık oranı`}
                >
                  <div
                    className="h-full bg-baglanti"
                    style={{ width: `${Math.round(p.acik_orani * 100)}%` }}
                  />
                </div>
                {digerleri.length > 0 ? (
                  <span className="text-xs text-pretty text-muted-foreground">
                    {digerleri
                      .map(
                        ([erisim, sayi]) => `${erisimEtiketi(erisim)}: ${sayi}`,
                      )
                      .join(" · ")}
                  </span>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function Servisler({ veri }: { veri: GozlemYaniti }) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-medium text-ana">Servis durumu</h3>
      <ul className="flex flex-col divide-y divide-kenar overflow-hidden rounded-xl border border-kenar">
        {veri.servisler.map((s) => {
          const ozet = servisOzeti(s);
          return (
            <li key={s.servis} className="flex flex-col gap-1 px-4 py-3">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="text-sm font-medium text-ana">
                  {servisEtiketi(s.servis)}
                </span>
                <DurumEtiketi metin={ozet.etiket} />
                <span className="ml-auto text-xs text-muted-foreground">
                  {servisSayilari(s)}
                </span>
              </div>
              {ozet.sorunlu && s.son_hata ? (
                <p className="text-xs text-muted-foreground">
                  Son hata: {tarihYaz(s.son_hata, true)}
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function DegerlendirmeOzeti({ veri }: { veri: GozlemYaniti }) {
  const d = veri.degerlendirme;
  if (d.sayi === 0) return null;
  return (
    <p className="text-sm text-pretty text-muted-foreground">
      {d.sayi} değerlendirme · ortalama {sureYaz(d.ortalama_sure_ms)} · yapay
      zekâya giden {d.girdi_token.toLocaleString("tr-TR")}, gelen{" "}
      {d.cikti_token.toLocaleString("tr-TR")} metin birimi.
    </p>
  );
}
