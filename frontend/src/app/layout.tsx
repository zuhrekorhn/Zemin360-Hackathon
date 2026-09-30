import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import { UstMenu } from "@/components/ust-menu";
import { OturumSaglayici } from "@/lib/oturum";

import "./globals.css";

// docs/design-language.md § Tipografi
// latin-ext alt kümesi zorunlu: ş, ğ, ı, ç, ö, ü doğru render edilmeli.
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin", "latin-ext"],
  display: "swap",
});

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600"],
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin", "latin-ext"],
  weight: ["400"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Zemin360 · Firma ve genç yetenek buluşma platformu",
  description:
    "Gençlerin çalışmalarını kanıtlı yetenek kartlarına, firmaların ihtiyaçlarını ölçülebilir kartlara dönüştüren; eşleşmeyi ve iş birliğini yapay zekâ desteğiyle takip eden açık kaynak platform.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="tr"
      className={`${fraunces.variable} ${plexSans.variable} ${plexMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        {/* Oturum (/me) tek yerde; menü ve giriş kapısı ondan okur. */}
        <OturumSaglayici>
          <UstMenu />
          {children}
        </OturumSaglayici>
      </body>
    </html>
  );
}
