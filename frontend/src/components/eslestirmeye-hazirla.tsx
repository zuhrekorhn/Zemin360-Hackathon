"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { hatayaCevir } from "@/lib/hata";

/**
 * Kart kaydedildi ama embedding'i hesaplanamadı (vektör servisine
 * ulaşılamadı). Böyle bir kart eşleştirmeye girmiyor; bunu gizlemek yerine
 * söylüyor ve yeniden denemenin yolunu veriyoruz.
 *
 * `hazirla` başarılı olunca üst bileşen kartı günceller (`embedding_var`
 * true olur) ve bu kutu kendiliğinden kaybolur.
 */
export function EslestirmeyeHazirla({
  hazirla,
}: {
  hazirla: () => Promise<unknown>;
}) {
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);

  async function dene() {
    setHata(null);
    setBekleniyor(true);
    try {
      await hazirla();
    } catch (sebep) {
      setHata(hatayaCevir(sebep).metin);
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <div
      role="status"
      className="flex flex-col gap-3 rounded-sm border border-kenar bg-muted px-4 py-3"
    >
      <p className="text-sm text-pretty">
        Kart kaydedildi, ancak henüz eşleşmeye hazır değil; o an bağlantı
        kurulamadı. Hazırlanana kadar öneri listelerinde görünmez.
      </p>
      {hata ? <p className="text-sm text-pretty">{hata}</p> : null}
      <Button
        type="button"
        size="lg"
        disabled={bekleniyor}
        onClick={() => void dene()}
        className="w-fit"
      >
        {bekleniyor ? "Hazırlanıyor…" : "Eşleştirmeye hazırla"}
      </Button>
    </div>
  );
}
