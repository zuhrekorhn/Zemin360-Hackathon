/**
 * Üç parçalı seviye çubuğu: güven göstergesinin her başlığı ve karşılama
 * sayfasındaki örnek aynı çubuğu kullanır (docs/design-language.md, "resmi
 * belge" dili: hairline, az yuvarlak).
 *
 * Seviye yalnızca renge dayanmaz: kelime her zaman görünür ya da (kelimeyi
 * çağıran ayrıca yazıyorsa) çubuğun kendi etiketi vardır.
 */

import { cn } from "@/lib/utils";

export function SeviyeCubugu({
  seviye,
  etiket,
  buyuk = false,
  genis = false,
}: {
  /** Dolu parça sayısı (0–3); null = değerlendirilmedi (hepsi boş, kesikli). */
  seviye: number | null;
  /** Ekran okuyucu için: "Seviye: Orta". */
  etiket: string;
  /** Karşılama sayfasındaki geniş çubuk. */
  buyuk?: boolean;
  /** Bulunduğu kutunun genişliğini doldurur (gösterge karoları). */
  genis?: boolean;
}) {
  return (
    <span
      role="img"
      aria-label={etiket}
      className={cn("flex gap-1", genis && "w-full")}
    >
      {[1, 2, 3].map((parca) => (
        <span
          key={parca}
          className={cn(
            "block rounded-[3px]",
            buyuk ? "h-2 w-[22px]" : genis ? "h-1.5 flex-1" : "h-1.5 w-4",
            seviye === null
              ? "border border-dashed border-kenar"
              : parca <= seviye
                ? seviye === 3
                  ? "bg-baglanti"
                  : "bg-ana"
                : "bg-kenar",
          )}
        />
      ))}
    </span>
  );
}
