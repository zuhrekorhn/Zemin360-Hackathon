"use client";

import Link from "next/link";
import { useState } from "react";

import { DogrulanmisFirma } from "@/components/dogrulanmis-firma";
import { DurumEtiketi, IletisimSatiri } from "@/components/panel";
import { Button } from "@/components/ui/button";
import type { GencEslesmesi, IhtiyacKartiYaniti } from "@/lib/api";
import {
  ILETISIM_ONAYI,
  ILETISIM_ONAYI_KUTUSU,
  NEDEN_UYGUN,
  gencDurumEtiketi,
  gencEylemleri,
  uyumMetni,
} from "@/lib/ilgi";
import {
  CALISMA_MODELI_ETIKETLERI,
  MUSAITLIK_ETIKETLERI,
  etiketle,
  sehirEtiketi,
} from "@/lib/sabitler";

/**
 * Gencin ana sayfasındaki fırsat ve ilgi satırları (docs/plans/genc-akisi.md § 7).
 * Metinler docs/icerik-rehberi.md'ye göre; liste docs/plans/genc-akisi-metinler.md.
 */

function IhtiyacOzeti({ ihtiyac }: { ihtiyac: IhtiyacKartiYaniti }) {
  const kosullar = [
    ihtiyac.sehir_tercihi ? sehirEtiketi(ihtiyac.sehir_tercihi) : null,
    ihtiyac.calisma_modeli
      ? etiketle(CALISMA_MODELI_ETIKETLERI, ihtiyac.calisma_modeli)
      : null,
    ihtiyac.musaitlik_tercihi
      ? etiketle(MUSAITLIK_ETIKETLERI, ihtiyac.musaitlik_tercihi)
      : null,
  ].filter(Boolean);
  return (
    <>
      <p className="text-sm text-pretty">{ihtiyac.problem_tanimi}</p>
      {ihtiyac.basari_kriteri ? (
        <p className="text-sm text-pretty text-muted-foreground">
          Başarı ölçütü: {ihtiyac.basari_kriteri}
        </p>
      ) : null}
      {kosullar.length > 0 ? (
        <p className="text-xs text-muted-foreground">{kosullar.join(" · ")}</p>
      ) : null}
    </>
  );
}

/** Bir fırsat: firma, ihtiyaç, uyum, "Neden uygun?" ve açık onaylı "İlgileniyorum". */
export function FirsatKarti({
  firsat,
  onIlgi,
}: {
  firsat: GencEslesmesi;
  onIlgi: () => Promise<void>;
}) {
  const [onayAcik, setOnayAcik] = useState(false);
  const [onaylandi, setOnaylandi] = useState(false);
  const [bekleniyor, setBekleniyor] = useState(false);
  const ihtiyac = firsat.ihtiyac_karti;

  async function ilet() {
    if (!onaylandi || bekleniyor) return;
    setBekleniyor(true);
    try {
      await onIlgi();
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <li className="flex flex-col gap-3 rounded-sm border border-kenar bg-card px-4 py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <span className="flex flex-wrap items-center gap-2 font-heading text-lg font-semibold text-ana">
          {ihtiyac.kurum.ad}
          <DogrulanmisFirma dogrulandi={ihtiyac.kurum.dogrulandi} />
        </span>
        <span className="rounded-sm border border-baglanti px-2 py-0.5 text-xs text-baglanti">
          {uyumMetni(firsat.uyum)}
        </span>
      </div>
      <IhtiyacOzeti ihtiyac={ihtiyac} />

      <section className="flex flex-col gap-1">
        <h4 className="font-heading text-sm font-semibold text-ana">
          {NEDEN_UYGUN}
        </h4>
        <p className="text-sm text-pretty text-muted-foreground">
          {firsat.gerekce_metni ?? "Açıklama henüz hazır değil."}
        </p>
      </section>

      <div className="flex flex-col gap-3 border-t border-kenar pt-3">
        {!onayAcik ? (
          <Button
            type="button"
            size="lg"
            className="w-fit"
            onClick={() => setOnayAcik(true)}
          >
            İlgileniyorum
          </Button>
        ) : (
          <div className="flex flex-col gap-3 rounded-sm border border-kenar bg-muted px-3 py-3">
            <p className="text-sm text-pretty">{ILETISIM_ONAYI}</p>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={onaylandi}
                onChange={(olay) => setOnaylandi(olay.target.checked)}
                className="accent-ana"
              />
              {ILETISIM_ONAYI_KUTUSU}
            </label>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                disabled={!onaylandi || bekleniyor}
                onClick={() => void ilet()}
              >
                {bekleniyor ? "İletiliyor…" : "İlgimi ilet"}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={bekleniyor}
                onClick={() => {
                  setOnayAcik(false);
                  setOnaylandi(false);
                }}
              >
                Vazgeç
              </Button>
            </div>
          </div>
        )}
      </div>
    </li>
  );
}

/** Gencin kendi ilgisi: durumu, geri çekme ya da karşılıklı ilgide iletişim. */
export function IlgiSatiri({
  ilgi,
  onGeriCek,
}: {
  ilgi: GencEslesmesi;
  onGeriCek: () => Promise<void>;
}) {
  const [bekleniyor, setBekleniyor] = useState(false);
  const ihtiyac = ilgi.ihtiyac_karti;
  const { geriCek } = gencEylemleri(ilgi.durum);

  async function cek() {
    if (
      !window.confirm(
        `${ihtiyac.kurum.ad} fırsatına gösterdiğin ilgi geri çekilsin mi?`,
      )
    ) {
      return;
    }
    setBekleniyor(true);
    try {
      await onGeriCek();
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <li className="flex flex-col gap-3 rounded-sm border border-kenar bg-card px-4 py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <span className="flex flex-wrap items-center gap-2 font-heading text-lg font-semibold text-ana">
          {ihtiyac.kurum.ad}
          <DogrulanmisFirma dogrulandi={ihtiyac.kurum.dogrulandi} />
        </span>
        <DurumEtiketi
          metin={gencDurumEtiketi(ilgi.durum)}
          baglanti={ilgi.durum === "kabul_edildi"}
        />
      </div>
      <IhtiyacOzeti ihtiyac={ihtiyac} />
      {ilgi.iletisim ? (
        <IletisimSatiri iletisim={ilgi.iletisim} karsiTaraf="kurum" />
      ) : null}
      {geriCek || ilgi.isbirligi_id ? (
        <div className="flex flex-wrap items-center gap-3 border-t border-kenar pt-3">
          {geriCek ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={bekleniyor}
              onClick={() => void cek()}
            >
              İlgimi geri çek
            </Button>
          ) : null}
          {ilgi.isbirligi_id ? (
            <Link
              href={`/isbirligi/${ilgi.isbirligi_id}`}
              className="text-sm text-baglanti underline"
            >
              İş birliğine git
            </Link>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}
