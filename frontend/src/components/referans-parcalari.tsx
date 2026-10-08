"use client";

import { useState } from "react";

import { OnayAlani } from "@/components/onay-alani";
import { FormAlani } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { FormDugmeleri } from "@/components/ui/form-dugmeleri";
import { Input } from "@/components/ui/input";
import type { ReferansDurumu } from "@/lib/api";
import { referansSatiri } from "@/lib/kart-duzenleme";
import { REFERANS_DURUMLARI, referansOzeti } from "@/lib/referans";

/**
 * Referans parçaları (docs/dogrulama.md § 7): istek formu ve bir referansın
 * satırı. E-postayı sistem gönderir; yanıt linki gence gösterilmez. Yanlış
 * adrese giden bekleyen istek geri çekilebilir; iddia değiştiyse eski yanıt
 * geçmişte kalır ve yeniden istenebilir (docs/kararlar.md G8).
 */

export function ReferansFormu({
  kimlik,
  bekleniyor,
  onIste,
  onVazgec,
}: {
  kimlik: string;
  bekleniyor: boolean;
  onIste: (eposta: string) => Promise<boolean>;
  onVazgec?: () => void;
}) {
  const [eposta, setEposta] = useState("");

  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(olay) => {
        olay.preventDefault();
        if (!eposta.trim()) return;
        void onIste(eposta.trim()).then((tamam) => {
          if (tamam) setEposta("");
        });
      }}
    >
      <FormAlani etiket="Referans iste" htmlFor={`referans-${kimlik}`}>
        <Input
          id={`referans-${kimlik}`}
          type="email"
          value={eposta}
          onChange={(olay) => setEposta(olay.target.value)}
          placeholder="ör. çalışmanı doğrulayabilecek birinin e-postası"
          autoComplete="off"
        />
      </FormAlani>
      <p className="text-xs text-pretty text-muted-foreground">
        Bu kişiye birkaç kısa soruluk bir e-posta göndeririz; 3. gün bir kez
        hatırlatırız. Yanıt için 7 günü var.
      </p>
      <FormDugmeleri onVazgec={onVazgec}>
        <Button type="submit" size="sm" disabled={bekleniyor || !eposta.trim()}>
          Referans iste
        </Button>
      </FormDugmeleri>
    </form>
  );
}

export function ReferansSatiri({
  referans,
  onYenidenIste,
  onGeriCek,
}: {
  referans: ReferansDurumu;
  onYenidenIste: () => void;
  onGeriCek: () => void;
}) {
  // İş değiştiyse eski yanıt geçmişte kalır (docs/kararlar.md G8).
  const { not, yenidenIstenebilir } = referansSatiri(referans);
  const { yanitlar, isaretler } = referansOzeti(referans);
  const [onayAcik, setOnayAcik] = useState(false);

  return (
    <div className="flex flex-col gap-1 rounded-lg border border-kenar px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm break-all">{referans.referans_email}</span>
        <span className="text-xs text-muted-foreground">
          {REFERANS_DURUMLARI[referans.durum] ?? referans.durum}
        </span>
      </div>

      {yanitlar.length > 0 ? (
        <p className="text-sm">{yanitlar.join(" · ")}</p>
      ) : null}
      {isaretler.length > 0 ? (
        <ul className="flex flex-wrap gap-1.5" aria-label="Referans hakkında">
          {isaretler.map((isaret) => (
            <li
              key={isaret}
              className="rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground"
            >
              {isaret}
            </li>
          ))}
        </ul>
      ) : null}

      {referans.yanit_metni ? (
        <p className="text-sm text-pretty text-muted-foreground">
          “{referans.yanit_metni}”
        </p>
      ) : null}

      {referans.geri_cekilebilir && onayAcik ? (
        <OnayAlani
          soru={`${referans.referans_email} adresine giden istek geri çekilsin mi? Bağlantı artık açılmaz; doğru adresle yeni bir referans isteyebilirsin.`}
          onayEtiketi="İsteği geri çek"
          onOnayla={() => {
            setOnayAcik(false);
            onGeriCek();
          }}
          onVazgec={() => setOnayAcik(false)}
        />
      ) : referans.geri_cekilebilir ? (
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="w-fit"
          onClick={() => setOnayAcik(true)}
        >
          Geri çek
        </Button>
      ) : null}

      {not ? (
        <p className="text-xs text-pretty text-muted-foreground">{not}</p>
      ) : null}
      {yenidenIstenebilir ? (
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="w-fit"
          onClick={onYenidenIste}
        >
          Referansı yeniden iste
        </Button>
      ) : null}
    </div>
  );
}
