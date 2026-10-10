"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";

/**
 * "E-posta yaz" ve onun yedekleri. `mailto:` bilgisayarın e-posta ayarına
 * bağlı: ayar yoksa işletim sistemi "hangi uygulama" diye sorar. Bu yüzden
 * ayara bağlı olmayan iki yol da yanında durur: Gmail'de dolu yazma penceresi
 * ve metni panoya kopyalamak. Taslak şablondan gelir (lib/eposta-taslagi.ts).
 */
export function EpostaEylemleri({
  eposta,
  konu,
  govde,
  href,
  gmailHref,
}: {
  eposta: string;
  konu: string;
  govde: string;
  href: string;
  gmailHref: string;
}) {
  const [kopyalandi, setKopyalandi] = useState(false);
  const zamanlayici = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (zamanlayici.current) clearTimeout(zamanlayici.current);
    },
    [],
  );

  async function kopyala() {
    const metin = [`Alıcı: ${eposta}`, `Konu: ${konu}`, "", govde].join("\n");
    try {
      await navigator.clipboard.writeText(metin);
      setKopyalandi(true);
      if (zamanlayici.current) clearTimeout(zamanlayici.current);
      zamanlayici.current = setTimeout(() => setKopyalandi(false), 2500);
    } catch {
      // Pano izni yoksa sessizce kalır; diğer iki yol açık.
    }
  }

  return (
    <span className="flex flex-wrap items-center gap-2">
      <Button asChild size="sm" variant="outline">
        <a href={href}>E-posta yaz</a>
      </Button>
      <Button asChild size="sm" variant="outline">
        <a href={gmailHref} target="_blank" rel="noopener noreferrer">
          Gmail&apos;de aç
        </a>
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        onClick={() => void kopyala()}
      >
        {kopyalandi ? "Kopyalandı" : "Metni kopyala"}
      </Button>
    </span>
  );
}
