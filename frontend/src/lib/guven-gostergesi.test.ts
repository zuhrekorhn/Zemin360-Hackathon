import { describe, expect, it } from "vitest";

import { baslikGosterimi } from "./guven-gostergesi";

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
