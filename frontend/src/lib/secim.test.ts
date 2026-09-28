import { describe, expect, it } from "vitest";

import { secimiDegistir } from "@/lib/secim";

const SECENEKLER = ["tam_zamanli", "yarim_zamanli", "proje_bazli", "staj"];

describe("secimiDegistir", () => {
  it("seçili olmayanı ekler, seçenek sırasını korur", () => {
    expect(secimiDegistir(SECENEKLER, ["staj"], "tam_zamanli")).toEqual([
      "tam_zamanli",
      "staj",
    ]);
  });

  it("seçili olanı çıkarır", () => {
    expect(secimiDegistir(SECENEKLER, ["tam_zamanli", "staj"], "staj")).toEqual([
      "tam_zamanli",
    ]);
  });

  it("listede olmayan eski değeri taşımaz", () => {
    expect(secimiDegistir(SECENEKLER, ["haftasonu"], "staj")).toEqual(["staj"]);
  });
});
