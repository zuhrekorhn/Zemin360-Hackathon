import { describe, expect, it } from "vitest";

import type { ReferansDurumu } from "@/lib/api";
import { formSorulari, referansOzeti } from "@/lib/referans";

function referans(ek: Partial<ReferansDurumu> = {}): ReferansDurumu {
  return {
    id: "r1",
    referans_email: "hoca@itu.edu.tr",
    durum: "yanitlandi",
    puan: null,
    iliski: null,
    iddia_dogru: null,
    pay_dogru: null,
    sonuc_dogru: null,
    yanit_metni: null,
    olusturma_tarihi: "2026-10-02T10:00:00Z",
    guc: null,
    guncel: true,
    yeniden_istenebilir: false,
    geri_cekilebilir: false,
    ...ek,
  };
}

describe("referansOzeti", () => {
  it("yanıtları soru adıyla, ilişkiyi ve güç işaretini ayrı gösterir", () => {
    const ozet = referansOzeti(
      referans({
        iliski: "ogretmen_danisman",
        iddia_dogru: "evet",
        pay_dogru: "kismen",
        guc: "egitim_eposta",
      }),
    );
    expect(ozet.yanitlar).toEqual(["Çalışma: evet", "Pay: kısmen"]);
    expect(ozet.isaretler).toEqual([
      "öğretmen / danışman",
      "Eğitim kurumu e-postası",
    ]);
  });

  it("eski 1-5 yanıtı olduğu gibi gösterir", () => {
    expect(referansOzeti(referans({ puan: 4 })).yanitlar).toEqual(["4/5"]);
  });

  it("bekleyen istekte yanıt yok", () => {
    const ozet = referansOzeti(referans({ durum: "bekliyor" }));
    expect(ozet.yanitlar).toEqual([]);
    expect(ozet.isaretler).toEqual([]);
  });
});

describe("formSorulari", () => {
  it("pay ve sonuç yazılmışsa ayrı sorular, iddia altında", () => {
    const sorular = formSorulari({ pay: "Arayüzü yazdım", sonuc: "%30 hız" });
    expect(sorular.map((s) => s.alan)).toEqual([
      "iddia_dogru",
      "pay_dogru",
      "sonuc_dogru",
    ]);
    expect(sorular[1].ayrinti).toBe("Arayüzü yazdım");
  });

  it("yazılmamış pay ya da sonuç sorulmaz", () => {
    expect(formSorulari({ pay: null, sonuc: "  " }).map((s) => s.alan)).toEqual(
      ["iddia_dogru"],
    );
  });
});
