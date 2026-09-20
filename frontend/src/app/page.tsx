import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { BackendDurumu } from "@/components/backend-durumu";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const ajanlar = [
  { ad: "Keşif", isi: "Genç yeteneği tanır, yetenek kartına dönüştürür" },
  { ad: "Tanımlama", isi: "Kurumun dağınık ihtiyacını netleştirir" },
  { ad: "Doğrulama", isi: "Somut çıktıları kanıt ve referansla sınar" },
  { ad: "Eşleştirme", isi: "Kart eşleşmesini gerekçesiyle birlikte önerir" },
  { ad: "Canlılık", isi: "Pasifleşen bağlantıları fark eder, hatırlatır" },
  { ad: "Takip", isi: "İş birliğini milestone bazında şeffaf tutar" },
];

const yollar = [
  {
    href: "/kesif",
    baslik: "Genç olarak başla",
    aciklama:
      "Keşif Ajanı'yla kısa bir sohbet. Ne yaptığını, neyi somut olarak ortaya çıkardığını birlikte yapılandırılmış bir yetenek kartına dönüştürürsünüz. CV yüklemek yok.",
  },
  {
    href: "/tanimlama",
    baslik: "Kurum olarak başla",
    aciklama:
      "Tanımlama Ajanı'yla kısa bir sohbet. “Dijitalleşmek istiyoruz” gibi bir cümleyi, ölçülebilir bir başarı kriteri olan net bir ihtiyaç kartına çevirirsiniz.",
  },
];

export default function AnaSayfa() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-12 px-6 py-16 sm:py-24">
      <header className="flex flex-col gap-5">
        <span className="w-fit rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
          Zemin360 Hackathon · GİRVAK
        </span>

        <h1 className="font-heading text-3xl leading-tight font-semibold text-balance sm:text-4xl">
          Genç yetenekler ve kurumlar, gerekçesi belli eşleşmelerle buluşsun.
        </h1>

        <p className="text-base text-pretty text-muted-foreground">
          Bu platform, keşif–doğrulama–eşleşme–takip döngüsünün tamamını tek bir
          paylaşılan veri katmanında birleştirir. Altı uzman yapay zeka ajanı
          aynı profil–ihtiyaç grafiği üzerinde çalışır; her eşleşme önerisi
          kara kutu bir skorla değil, neden eşleştiğini anlatan bir gerekçeyle
          gelir.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2">
        {yollar.map((yol) => (
          <Card key={yol.href} className="justify-between">
            <CardHeader>
              <CardTitle className="text-lg">{yol.baslik}</CardTitle>
              <CardDescription className="text-pretty">
                {yol.aciklama}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild size="lg" className="w-full">
                <Link href={yol.href}>
                  {yol.baslik}
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="font-heading text-sm font-medium text-muted-foreground">
          Altı problem, altı ajan
        </h2>
        <ul className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
          {ajanlar.map((ajan) => (
            <li key={ajan.ad} className="flex flex-col">
              <span className="text-sm font-medium">{ajan.ad} Ajanı</span>
              <span className="text-sm text-muted-foreground">{ajan.isi}</span>
            </li>
          ))}
        </ul>
      </section>

      <footer className="mt-auto flex flex-col gap-4 border-t border-border pt-8">
        <BackendDurumu />
        <p className="text-xs text-muted-foreground">
          Faz 1 — iskelet. Ajan sohbetleri henüz bağlanmadı.
        </p>
      </footer>
    </main>
  );
}
