import { describe, expect, it } from "vitest";

import { uygunlukRozeti } from "./uygunluk";

describe("uygunlukRozeti", () => {
  it("yalnızca kısmen uygun için rozet metni verir", () => {
    expect(uygunlukRozeti("kismen")).toBe("Kısmen uygun");
    expect(uygunlukRozeti("uygun")).toBeNull();
    expect(uygunlukRozeti(null)).toBeNull();
    expect(uygunlukRozeti(undefined)).toBeNull();
  });
});
