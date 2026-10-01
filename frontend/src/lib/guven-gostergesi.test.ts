import { describe, expect, it } from "vitest";

import { baslikGosterimi, gostergeDoluMu } from "./guven-gostergesi";

describe("baslikGosterimi", () => {
  it("değerlendirilmemiş başlık 0 değil, tire gösterir", () => {
    expect(baslikGosterimi("Kanıt", null)).toEqual({
      metin: "—",
      sozlu: "değerlendirilmedi",
    });
  });

  it("referans yoksa 'referans yok' der", () => {
    expect(baslikGosterimi("Referans", null).sozlu).toBe("referans yok");
  });

  it("0 bir değerlendirme sonucudur, tire değildir", () => {
    expect(baslikGosterimi("Referans", 0)).toEqual({
      metin: "0/3",
      sozlu: "3 üzerinden 0",
    });
  });
});

describe("gostergeDoluMu", () => {
  const bos = {
    kanit_orijinalligi: null,
    sonuc_olculebilirligi: null,
    rol_netligi: null,
    ucuncu_taraf_onayi: null,
    gerekce_metni: null,
  };

  it("gösterge yoksa ya da dört başlık da boşsa hayır", () => {
    expect(gostergeDoluMu(null)).toBe(false);
    expect(gostergeDoluMu(bos)).toBe(false);
  });

  it("tek bir başlık doluysa evet (0 da dolu sayılır)", () => {
    expect(gostergeDoluMu({ ...bos, ucuncu_taraf_onayi: 0 })).toBe(true);
  });
});
