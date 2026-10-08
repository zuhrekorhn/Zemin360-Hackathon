import { describe, expect, it } from "vitest";

import { sekmeBasligi } from "@/lib/sekme-basligi";

describe("sekmeBasligi", () => {
  it("sayfa adını markayla birleştirir", () => {
    expect(sekmeBasligi("Panelim")).toBe("Panelim · Zemin360");
  });

  it("boş ad yalnızca marka olur", () => {
    expect(sekmeBasligi("")).toBe("Zemin360");
    expect(sekmeBasligi("   ")).toBe("Zemin360");
    expect(sekmeBasligi(null)).toBe("Zemin360");
    expect(sekmeBasligi(undefined)).toBe("Zemin360");
  });
});
