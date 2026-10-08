import { describe, expect, it } from "vitest";

import { adGosterimi } from "@/lib/ad";

describe("adGosterimi", () => {
  it("kelimelerin ilk harfi büyük, Türkçe kuralıyla", () => {
    expect(adGosterimi("zhre")).toBe("Zhre");
    expect(adGosterimi("  ilkay  özdemir ")).toBe("İlkay Özdemir");
    expect(adGosterimi("Elif Demir")).toBe("Elif Demir");
  });
});
