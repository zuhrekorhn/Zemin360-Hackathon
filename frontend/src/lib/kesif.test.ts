import { describe, expect, it } from "vitest";

import type { KartTaslagi } from "@/lib/api";
import { toplananlar } from "@/lib/kesif";

const tamamlar = (taslak: KartTaslagi | null) =>
  toplananlar(taslak)
    .filter((b) => b.tamam)
    .map((b) => b.anahtar);

describe("toplananlar", () => {
  it("taslak yokken hiçbiri tamam değil; kanıt isteğe bağlı", () => {
    const liste = toplananlar(null);
    expect(liste.every((b) => !b.tamam)).toBe(true);
    expect(liste.find((b) => b.anahtar === "kanit")?.istegeBagli).toBe(true);
  });

  it("sohbet ilerledikçe dolar", () => {
    expect(
      tamamlar({
        rol_alani: "Backend geliştirici",
        deneyim_seviyesi: null,
        sektor_ilgi_alani: [],
        araclar_teknolojiler: ["Python"],
        somut_ciktilar: [
          {
            baslik: "Dernek sistemi",
            aciklama: null,
            kanit_linki: null,
            kendi_rolu: "Backend'i yazdım",
            referans_email: "r@ornek.com",
          },
        ],
      }),
    ).toEqual(["rol", "arac", "calisma", "pay", "kanit"]);
  });
});
