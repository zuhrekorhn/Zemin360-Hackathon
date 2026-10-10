import { describe, expect, it } from "vitest";

import { CIKIS_PENCERESI_MS, cikisYeniMi, cikisiIsaretle } from "@/lib/cikis";

describe("bilinçli çıkış", () => {
  it("çıkıştan hemen sonra yeni sayılır, süre geçince sayılmaz", () => {
    const t = 1_000_000;
    cikisiIsaretle(t);
    expect(cikisYeniMi(t + 10)).toBe(true);
    expect(cikisYeniMi(t + CIKIS_PENCERESI_MS - 1)).toBe(true);
    expect(cikisYeniMi(t + CIKIS_PENCERESI_MS)).toBe(false);
  });
});
