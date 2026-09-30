import { describe, expect, it } from "vitest";

import { klavyeyleSekme } from "@/lib/sekme";

describe("klavyeyleSekme", () => {
  it("sağ ok sonrakine geçer, sonda başa sarar", () => {
    expect(klavyeyleSekme(0, "ArrowRight", 2)).toBe(1);
    expect(klavyeyleSekme(1, "ArrowRight", 2)).toBe(0);
  });

  it("sol ok öncekine geçer, başta sona sarar", () => {
    expect(klavyeyleSekme(1, "ArrowLeft", 2)).toBe(0);
    expect(klavyeyleSekme(0, "ArrowLeft", 2)).toBe(1);
  });

  it("Home ilk, End son sekmeye gider", () => {
    expect(klavyeyleSekme(2, "Home", 3)).toBe(0);
    expect(klavyeyleSekme(0, "End", 3)).toBe(2);
  });

  it("gezinme olmayan tuşta null döner", () => {
    expect(klavyeyleSekme(0, "Tab", 2)).toBeNull();
    expect(klavyeyleSekme(0, "Enter", 2)).toBeNull();
  });

  it("sekme yoksa null döner", () => {
    expect(klavyeyleSekme(0, "ArrowRight", 0)).toBeNull();
  });
});
