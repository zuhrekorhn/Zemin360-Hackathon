import { describe, expect, it } from "vitest";

import { KAPANMA_NEDENLERI, ilanKapali, ilanlariSirala } from "@/lib/ilan";

describe("KAPANMA_NEDENLERI", () => {
  it("backend'deki üç neden, sabit sırada", () => {
    expect(KAPANMA_NEDENLERI.map((n) => n.deger)).toEqual([
      "platformda_bulundu",
      "baska_yoldan_bulundu",
      "vazgecildi",
    ]);
  });
});

describe("ilanlariSirala", () => {
  it("açıklar önce, kapalılar sonda; grup içi sıra korunur", () => {
    const ilanlar = [
      { id: "a", durum: "kapandi" },
      { id: "b", durum: "acik" },
      { id: "c", durum: "kapandi" },
      { id: "d", durum: "acik" },
    ];
    expect(ilanlariSirala(ilanlar).map((i) => i.id)).toEqual([
      "b",
      "d",
      "a",
      "c",
    ]);
  });

  it("ilanKapali", () => {
    expect(ilanKapali({ durum: "kapandi" })).toBe(true);
    expect(ilanKapali({ durum: "acik" })).toBe(false);
  });
});
