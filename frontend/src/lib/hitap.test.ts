import { describe, expect, it } from "vitest";

import { hitapRolden, hitapla } from "@/lib/hitap";

describe("hitap", () => {
  it("gence sen, firmaya ve GİRVAK'a siz, ziyaretçiye sen", () => {
    expect(hitapRolden("genc")).toBe("sen");
    expect(hitapRolden("kurum")).toBe("siz");
    expect(hitapRolden("girvak")).toBe("siz");
    expect(hitapRolden(null)).toBe("sen");
  });

  it("hitapla doğru hâli seçer", () => {
    expect(hitapla("sen", "Tekrar dene", "Tekrar deneyin")).toBe("Tekrar dene");
    expect(hitapla("siz", "Tekrar dene", "Tekrar deneyin")).toBe(
      "Tekrar deneyin",
    );
  });
});
