"use client";

import Link from "next/link";
import { useEffect } from "react";

import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { Button } from "@/components/ui/button";

/**
 * Beklenmedik arayüz hatası (docs/icerik-rehberi.md § 5.4): ne oldu ve ne
 * yapılabilir, teknik ayrıntı yok. Hangi rolün baktığı bilinmeyebilir, bu yüzden hitapsız.
 */
export default function Hata({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <Sayfa genislik="form">
      <SayfaBasligi
        baslik="Sayfa şu an açılamadı"
        aciklama="Beklenmedik bir sorun oluştu. Yeniden yüklemek çoğu zaman yeter; sorun sürerse ana sayfadan devam edilebilir."
      />
      <div className="flex flex-wrap gap-3">
        <Button type="button" size="lg" onClick={reset}>
          Yeniden yükle
        </Button>
        <Button asChild variant="outline" size="lg">
          <Link href="/">Ana sayfaya git</Link>
        </Button>
      </div>
    </Sayfa>
  );
}
