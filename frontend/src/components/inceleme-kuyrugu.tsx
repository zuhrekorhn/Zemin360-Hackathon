"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { BosDurum, PanelBolumu, tarihYaz } from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  type IncelemeSatiri,
  girvakIncelemeKarari,
  girvakIncelemeler,
  kanitDosyasiAdresi,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import {
  ayrintiSatirlari,
  incelenecekBelgeler,
  karsilastirilacakKartlar,
  kararEtiketleri,
  turEtiketi,
} from "@/lib/inceleme";

/**
 * GİRVAK: inceleme kuyruğu (docs/plans/dogrulama-iyilestirme.md § 9).
 *
 * Sistem işaret açar, karar GİRVAK'ın; işaret puanı kendiliğinden
 * değiştirmez. Karar gence bildirilir; not isteğe bağlıdır ve bildirimde
 * görünür. Karar verilen işaret listeden çıkar.
 */
export function IncelemeKuyrugu() {
  const [isaretler, setIsaretler] = useState<IncelemeSatiri[] | null>(null);
  const [notlar, setNotlar] = useState<Record<string, string>>({});
  const [isleniyor, setIsleniyor] = useState<string | null>(null);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      setIsaretler(await girvakIncelemeler());
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, []);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku();
  }, [oku]);

  async function karar(id: string, secim: "kapandi" | "dogrulanamadi") {
    setHata(null);
    setIsleniyor(id);
    try {
      await girvakIncelemeKarari(id, secim, notlar[id]?.trim() || null);
      setIsaretler((liste) => liste?.filter((i) => i.id !== id) ?? null);
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setIsleniyor(null);
    }
  }

  return (
    <PanelBolumu
      id="inceleme"
      baslik="İnceleme kuyruğu"
      aciklama="Sistemin gördüğü sinyaller ve gençlerin talepleri. İşaret puanı kendiliğinden değiştirmez; kararı siz verirsiniz ve genç sonucu bildirim olarak görür."
    >
      {hata ? <HataKutusu hata={hata} tekrarDene={() => void oku()} /> : null}
      {isaretler === null ? null : isaretler.length === 0 ? (
        <BosDurum metin="İncelenecek bir şey yok." />
      ) : (
        <ul className="flex flex-col divide-y divide-kenar rounded-sm border border-kenar">
          {isaretler.map((isaret) => {
            const etiketler = kararEtiketleri(isaret.tur);
            const notAlani = `inceleme-notu-${isaret.id}`;
            return (
              <li key={isaret.id} className="flex flex-col gap-2 px-4 py-3">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <span className="font-medium text-ana">
                    {turEtiketi(isaret.tur)}
                  </span>
                  <span className="text-sm">
                    {isaret.genc_adi ?? "—"}
                    {isaret.cikti_basligi ? ` · ${isaret.cikti_basligi}` : ""}
                  </span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {tarihYaz(isaret.olusturma_tarihi)}
                  </span>
                </div>
                {ayrintiSatirlari(isaret).map((satir, i) => (
                  <p key={i} className="text-sm text-pretty">
                    {satir}
                  </p>
                ))}
                {isaret.somut_cikti_id
                  ? incelenecekBelgeler(isaret).map((parcaId, i) => (
                      <Button
                        key={parcaId}
                        type="button"
                        size="sm"
                        variant="outline"
                        className="w-fit"
                        onClick={() =>
                          void kanitDosyasiAdresi(
                            isaret.somut_cikti_id!,
                            parcaId,
                          )
                            .then(({ adres }) => window.location.assign(adres))
                            .catch((sebep) => setHata(hatayaCevir(sebep)))
                        }
                      >
                        {i === 0 ? "Belgeyi indir" : `${i + 1}. belgeyi indir`}
                      </Button>
                    ))
                  : null}
                {isaret.kart_id ? (
                  <Link
                    href={`/kart/${isaret.kart_id}`}
                    className="w-fit text-sm text-baglanti underline"
                  >
                    Kartı aç
                  </Link>
                ) : null}
                {karsilastirilacakKartlar(isaret).map((kartId, i) => (
                  <Link
                    key={kartId}
                    href={`/kart/${kartId}`}
                    className="w-fit text-sm text-baglanti underline"
                  >
                    {i === 0 ? "Öteki kartı aç" : `${i + 1}. öteki kartı aç`}
                  </Link>
                ))}
                <label htmlFor={notAlani} className="sr-only">
                  Gence not (isteğe bağlı)
                </label>
                <Input
                  id={notAlani}
                  type="text"
                  maxLength={500}
                  placeholder="Gence not (isteğe bağlı)"
                  value={notlar[isaret.id] ?? ""}
                  onChange={(olay) =>
                    setNotlar((onceki) => ({
                      ...onceki,
                      [isaret.id]: olay.target.value,
                    }))
                  }
                />
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    disabled={isleniyor !== null}
                    onClick={() => void karar(isaret.id, "kapandi")}
                  >
                    {etiketler.kapandi}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={isleniyor !== null}
                    onClick={() => void karar(isaret.id, "dogrulanamadi")}
                  >
                    {etiketler.dogrulanamadi}
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </PanelBolumu>
  );
}
