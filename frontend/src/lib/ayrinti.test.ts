import { describe, expect, it } from "vitest";

import { ayrintiyiOku } from "@/lib/ayrinti";

describe("ayrintiyiOku", () => {
  it("uçun kendi cümlesini aynen döner", () => {
    expect(ayrintiyiOku("Bu e-postayla bir hesap zaten var.")).toBe(
      "Bu e-postayla bir hesap zaten var.",
    );
  });

  // Yalnızca bizim yazdığımız ("Value error, ") cümleler; İngilizce şema
  // metinleri kullanıcıya gösterilmez (rehber § 5.4).
  it("şema hatalarını okunur cümleye çevirir, önekini, tekrarı ve İngilizceyi atar", () => {
    expect(
      ayrintiyiOku([
        {
          loc: ["body"],
          msg: "Value error, KVKK aydınlatma metni onaylanmalı",
        },
        {
          loc: ["body", "x"],
          msg: "Value error, KVKK aydınlatma metni onaylanmalı",
        },
        {
          loc: ["body", "sinif"],
          msg: "Input should be less than or equal to 8",
        },
      ]),
    ).toBe("KVKK aydınlatma metni onaylanmalı");
  });

  it("tanınmayan gövdede undefined", () => {
    expect(ayrintiyiOku(undefined)).toBeUndefined();
    expect(ayrintiyiOku([])).toBeUndefined();
    expect(ayrintiyiOku({ baska: 1 })).toBeUndefined();
  });
});
