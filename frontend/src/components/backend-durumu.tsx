"use client";

import { useEffect, useState } from "react";

import { API_URL, saglikKontrol } from "@/lib/api";

type Durum = "kontrol_ediliyor" | "bagli" | "bagli_degil";

const gorunum: Record<Durum, { nokta: string; metin: string }> = {
  kontrol_ediliyor: {
    nokta: "bg-muted-foreground animate-pulse",
    metin: "Backend kontrol ediliyor…",
  },
  bagli: { nokta: "bg-emerald-500", metin: "Backend bağlı" },
  bagli_degil: { nokta: "bg-destructive", metin: "Backend'e ulaşılamıyor" },
};

/**
 * Frontend ile backend'in gerçekten konuştuğunu doğrulayan küçük gösterge.
 * Faz 1 iskelet doğrulaması — ileride kaldırılabilir.
 */
export function BackendDurumu() {
  const [durum, setDurum] = useState<Durum>("kontrol_ediliyor");

  useEffect(() => {
    let iptal = false;

    saglikKontrol()
      .then((yanit) => {
        if (!iptal) setDurum(yanit.status === "ok" ? "bagli" : "bagli_degil");
      })
      .catch(() => {
        if (!iptal) setDurum("bagli_degil");
      });

    return () => {
      iptal = true;
    };
  }, []);

  const { nokta, metin } = gorunum[durum];

  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground">
      <span
        aria-hidden="true"
        className={`size-2 shrink-0 rounded-full ${nokta}`}
      />
      <span>{metin}</span>
      <code className="font-mono text-[0.7rem] opacity-60">{API_URL}</code>
    </div>
  );
}
