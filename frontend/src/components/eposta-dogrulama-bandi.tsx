"use client";

/**
 * Kayıt e-postası doğrulanmamışsa panelde görünen bant
 * (docs/dogrulama.md § 6.3). Engellemez: hesap her şeyi
 * kullanır; bant yalnızca bağlantıyı hatırlatır ve yenisini gönderir.
 */

import { Mail } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { KUTU } from "@/components/ui/yuzey";
import { dogrulamaBaglantisiGonder, type MeYaniti } from "@/lib/api";
import { hatayaCevir } from "@/lib/hata";
import { hitapla, hitapRolden } from "@/lib/hitap";
import { cn } from "@/lib/utils";

export function EpostaDogrulamaBandi({ hesap }: { hesap: MeYaniti }) {
  const [durum, setDurum] = useState<"bos" | "gonderiliyor" | "gonderildi">(
    "bos",
  );
  const [hata, setHata] = useState<string | null>(null);

  if (hesap.eposta_dogrulandi || hesap.rol === "girvak") return null;
  const hitap = hitapRolden(hesap.rol);

  async function gonder() {
    setDurum("gonderiliyor");
    setHata(null);
    try {
      await dogrulamaBaglantisiGonder();
      setDurum("gonderildi");
    } catch (sebep) {
      setHata(hatayaCevir(sebep).metin);
      setDurum("bos");
    }
  }

  return (
    <div
      role="note"
      className={cn(
        KUTU,
        "flex flex-wrap items-center gap-x-4 gap-y-2 border-l-[3px] border-l-vurgu px-5 py-4 text-sm text-pretty",
      )}
    >
      <Mail aria-hidden="true" className="size-5 shrink-0 text-ana" />
      <span className="min-w-0 flex-1 basis-64">
        {hitapla(
          hitap,
          `E-posta adresini henüz doğrulamadın. ${hesap.email} adresine gönderdiğimiz bağlantıyı aç.`,
          `E-posta adresinizi henüz doğrulamadınız. ${hesap.email} adresine gönderdiğimiz bağlantıyı açın.`,
        )}
      </span>
      {durum === "gonderildi" ? (
        <span role="status">Yeni bağlantı gönderildi.</span>
      ) : (
        <Button
          variant="outline"
          size="sm"
          disabled={durum === "gonderiliyor"}
          onClick={() => void gonder()}
        >
          Bağlantıyı yeniden gönder
        </Button>
      )}
      {hata ? (
        <span role="alert" className="text-destructive">
          {hata}
        </span>
      ) : null}
    </div>
  );
}
