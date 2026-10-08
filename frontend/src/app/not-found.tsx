import Link from "next/link";

import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { Button } from "@/components/ui/button";

/** Olmayan adres (docs/icerik-rehberi.md § 5.4, § 5.5): ne yok, neden, ilk adım. */
export default function BulunamadiSayfasi() {
  return (
    <Sayfa genislik="form">
      <SayfaBasligi
        baslik="Bu sayfa bulunamadı"
        aciklama="Adres yanlış yazılmış ya da sayfa kaldırılmış olabilir."
      />
      <div>
        <Button asChild size="lg">
          <Link href="/">Ana sayfaya git</Link>
        </Button>
      </div>
    </Sayfa>
  );
}
