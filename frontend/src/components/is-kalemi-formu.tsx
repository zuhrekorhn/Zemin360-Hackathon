"use client";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { SomutCiktiTaslagi } from "@/lib/api";
import { IS_TURU_ETIKETLERI } from "@/lib/sabitler";

type Alan = Exclude<keyof SomutCiktiTaslagi, "baslik"> | "baslik";

type AlanTanimi = {
  ad: Alan;
  etiket: string;
  ornek?: string;
  tur?: "url" | "email";
  /** Cümle uzunluğundaki metinler tek satırda kesilmesin diye. */
  cokSatir?: boolean;
};

const ALANLAR: AlanTanimi[] = [
  { ad: "baslik", etiket: "Başlık" },
  {
    ad: "aciklama",
    etiket: "Açıklama",
    ornek: "ör. Ne yaptın, ne ortaya çıktı?",
    cokSatir: true,
  },
  {
    ad: "olculebilir_sonuc",
    etiket: "Sonuç (sayıyla)",
    ornek: "ör. 400 kitap ve 120 üye takip ediliyor",
    cokSatir: true,
  },
  {
    ad: "kendi_rolu",
    etiket: "Senin payın",
    ornek: "ör. Backend'i ben yazdım",
    cokSatir: true,
  },
  {
    ad: "kanit_linki",
    etiket: "Kanıt linki",
    ornek: "ör. github.com/… ya da bir demo adresi",
    tur: "url",
  },
  {
    ad: "referans_email",
    etiket: "Referans kişinin e-postası",
    ornek: "ör. çalışmanı doğrulayabilecek birinin e-postası",
    tur: "email",
  },
];

/**
 * Bir iş kaleminin düzenlenebilir alanları. Keşif taslağı önizlemesi ve
 * "Yeni iş ekle" aynı parçayı kullanır (docs/plans/genc-akisi.md § 5.4).
 * Referans e-postası kurumlarla paylaşılmaz; kanıt iş kalemine bağlıdır.
 */
export function IsKalemiFormu({
  kimlik,
  cikti,
  onDegis,
  referansGoster = true,
}: {
  /** Aynı sayfada birden çok form varsa id'ler çakışmasın. */
  kimlik: string;
  cikti: SomutCiktiTaslagi;
  onDegis: (alan: keyof SomutCiktiTaslagi, deger: string) => void;
  /** Kayıtlı kalemde referans, kart sayfasının referans akışıyla eklenir. */
  referansGoster?: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      <label
        htmlFor={`${kimlik}-is_turu`}
        className="text-xs text-muted-foreground"
      >
        Türü
      </label>
      <select
        id={`${kimlik}-is_turu`}
        value={cikti.is_turu ?? ""}
        onChange={(olay) => onDegis("is_turu", olay.target.value)}
        className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
      >
        <option value="">Belirtilmedi</option>
        {Object.entries(IS_TURU_ETIKETLERI).map(([deger, etiket]) => (
          <option key={deger} value={deger}>
            {etiket}
          </option>
        ))}
      </select>
      {ALANLAR.filter((a) => referansGoster || a.ad !== "referans_email").map(
        (alan) => (
          <div key={alan.ad} className="flex flex-col gap-1">
            <label
              htmlFor={`${kimlik}-${alan.ad}`}
              className="text-xs text-muted-foreground"
            >
              {alan.etiket}
            </label>
            <AlanKutusu
              kimlik={`${kimlik}-${alan.ad}`}
              alan={alan}
              deger={(cikti[alan.ad] as string | null | undefined) ?? ""}
              onDegis={(deger) => onDegis(alan.ad, deger)}
            />
          </div>
        ),
      )}
    </div>
  );
}

function AlanKutusu({
  kimlik,
  alan,
  deger,
  onDegis,
}: {
  kimlik: string;
  alan: AlanTanimi;
  deger: string;
  onDegis: (deger: string) => void;
}) {
  const ortak = {
    id: kimlik,
    value: deger,
    placeholder: alan.ornek,
    required: alan.ad === "baslik",
  };
  if (alan.cokSatir) {
    return (
      <Textarea
        {...ortak}
        rows={2}
        onChange={(olay) => onDegis(olay.target.value)}
      />
    );
  }
  return (
    <Input
      {...ortak}
      inputMode={alan.tur}
      onChange={(olay) => onDegis(olay.target.value)}
    />
  );
}
