import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

// latin-ext: Türkçe karakterler (ş, ğ, İ, ı) için gerekli
const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin", "latin-ext"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin", "latin-ext"],
});

export const metadata: Metadata = {
  title: "Zemin360 — Kurum ve genç yetenek buluşma platformu",
  description:
    "Keşif, doğrulama, eşleşme ve iş birliği takibini tek bir paylaşılan veri katmanında birleştiren, altı uzman yapay zeka ajanından oluşan açık kaynak platform.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="tr"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
