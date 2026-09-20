import Link from "next/link";

import { Button } from "@/components/ui/button";

// Faz 1 iskeleti: ana sayfadaki yönlendirme kırık link olmasın diye duruyor.
// Keşif Ajanı sohbet arayüzü buraya gelecek (docs/agent-specs.md § 1).
export default function KesifSayfasi() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-16 sm:py-24">
      <h1 className="font-heading text-2xl font-semibold text-secondary">
        Keşif Ajanı
      </h1>
      <p className="text-muted-foreground">
        Yetenek kartı sohbeti burada açılacak. Henüz bağlanmadı.
      </p>
      <Button asChild variant="outline" className="w-fit">
        <Link href="/">Ana sayfaya dön</Link>
      </Button>
    </main>
  );
}
