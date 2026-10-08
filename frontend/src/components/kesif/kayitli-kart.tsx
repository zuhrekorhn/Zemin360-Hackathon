"use client";

import { FileCheck2, Search, UserCheck } from "lucide-react";
import Link from "next/link";

import { EslestirmeyeHazirla } from "@/components/eslestirmeye-hazirla";
import { KUTU } from "@/components/ui/yuzey";
import { type YetenekKartiYaniti, yetenekKartiHazirla } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Onaydan hemen sonra: kartın hazır olduğunu söyleyen bant ve üç sonraki adım.
 * Kartın tamamı kart sayfasında; burada tekrar dökülmez.
 */
export function KayitliKart({
  kart,
  onGuncelle,
}: {
  kart: YetenekKartiYaniti;
  onGuncelle: (kart: YetenekKartiYaniti) => void;
}) {
  const kartYolu = `/kart/${kart.id}`;
  const adimlar = [
    {
      ikon: FileCheck2,
      baslik: "Kanıt ekle",
      metin:
        "Çalışmalarının linkini ya da dosyasını ekle; güven göstergen güçlenir.",
      href: kartYolu,
    },
    {
      ikon: UserCheck,
      baslik: "Referans iste",
      metin:
        "Çalışmanı bilen birine kısa bir e-posta gider; yanıtı kartına eklenir.",
      href: kartYolu,
    },
    {
      ikon: Search,
      baslik: "Fırsatlara bak",
      metin: "Kartın firmaların ihtiyaçlarıyla eşleşir; uygun olanlar burada.",
      href: "/genc",
    },
  ];

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 rounded-xl bg-ana px-7 py-7 text-zemin sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-1.5">
          <p className="text-xs font-medium text-zemin/70">Kartın kaydedildi</p>
          <h2 className="font-heading text-2xl font-semibold text-balance">
            Kartın hazır
          </h2>
          <p className="max-w-prose text-[15px] text-pretty text-zemin/85">
            {kart.somut_ciktilar.length} çalışmayla kaydedildi.
            {kart.embedding_var
              ? " Firmaların ihtiyaçlarıyla eşleşmeye başladı."
              : null}
            {kart.kanit_bekleyen
              ? " Bazı çalışmaların kanıt bekliyor; kanıt ekledikçe öne çıkarsın."
              : null}
          </p>
        </div>
        <Link
          href={kartYolu}
          className="inline-flex h-10 shrink-0 items-center justify-center self-start rounded-lg bg-vurgu px-5 text-sm font-semibold text-metin hover:bg-vurgu/90 sm:self-center"
        >
          Kartına git
        </Link>
      </div>

      {kart.embedding_var ? null : (
        <EslestirmeyeHazirla
          hazirla={async () => onGuncelle(await yetenekKartiHazirla(kart.id))}
        />
      )}

      <div className="flex flex-col gap-3">
        <h3 className="font-heading text-lg font-semibold text-ana">
          Sırada ne var
        </h3>
        <ul className="grid gap-3 sm:grid-cols-3">
          {adimlar.map(({ ikon: Ikon, baslik, metin, href }) => (
            <li key={baslik}>
              <Link
                href={href}
                className={cn(
                  KUTU,
                  "flex h-full flex-col gap-2 px-5 py-5 transition-colors hover:border-ana",
                )}
              >
                <Ikon aria-hidden="true" className="size-5 text-baglanti" />
                <span className="font-medium text-ana">{baslik}</span>
                <span className="text-sm text-pretty text-muted-foreground">
                  {metin}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
