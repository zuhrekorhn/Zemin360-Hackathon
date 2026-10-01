"use client";

import Link from "next/link";

import { EslestirmeyeHazirla } from "@/components/eslestirmeye-hazirla";
import { KartOnizleme } from "@/components/kesif/kart-onizleme";
import { Button } from "@/components/ui/button";
import { type YetenekKartiYaniti, yetenekKartiHazirla } from "@/lib/api";
import { kayitliCiktiTaslagi } from "@/lib/kanit";

/** Onaydan hemen sonra: kaydedilen kart ve kart sayfasına geçiş. */
export function KayitliKart({
  kart,
  onGuncelle,
}: {
  kart: YetenekKartiYaniti;
  onGuncelle: (kart: YetenekKartiYaniti) => void;
}) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-heading text-xl font-semibold text-ana">
        Kartın kaydedildi
      </h2>
      {kart.embedding_var ? (
        <p className="text-sm text-pretty text-muted-foreground">
          Artık firmaların ihtiyaçlarıyla eşleştirilebilir.
          {kart.kanit_bekleyen
            ? " Bazı çalışmaların kanıt bekliyor; kanıt eklersen kartın daha güçlü görünür."
            : null}
        </p>
      ) : (
        <EslestirmeyeHazirla
          hazirla={async () => onGuncelle(await yetenekKartiHazirla(kart.id))}
        />
      )}

      <KartOnizleme
        taslak={{
          rol_alani: kart.rol_alani,
          deneyim_seviyesi: kart.deneyim_seviyesi,
          sektor_ilgi_alani: kart.sektor_ilgi_alani,
          araclar_teknolojiler: kart.araclar_teknolojiler,
          sertifikalar: kart.sertifikalar,
          diller: kart.diller,
          somut_ciktilar: kart.somut_ciktilar.map(kayitliCiktiTaslagi),
        }}
      />

      <p className="font-mono text-xs text-muted-foreground">
        {/* Sadece id kırılsın; "sürüm" kelimesi dar ekranda ortadan bölünmesin. */}
        kart no: <span className="break-all">{kart.id}</span> · sürüm{" "}
        {kart.versiyon}
      </p>

      <Button asChild size="lg" className="mt-1 w-fit">
        <Link href={`/kart/${kart.id}`}>
          {/* Her çalışmanın linki ya da referansı varsa eklenecek kanıt yok. */}
          {kart.kanit_bekleyen ? "Kanıt ekle ve doğrulat" : "Kartına git"}
        </Link>
      </Button>
    </section>
  );
}
