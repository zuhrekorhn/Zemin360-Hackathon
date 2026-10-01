import { describe, expect, it } from "vitest";

import type { GuvenSkoru, SomutCiktiYaniti } from "@/lib/api";

import {
  degerlendirildiMi,
  kanitAdresi,
  kanitLinkleri,
  kayitliCiktiTaslagi,
} from "./kanit";

const skor = (degisiklik: Partial<GuvenSkoru> = {}): GuvenSkoru => ({
  kanit_orijinalligi: null,
  sonuc_olculebilirligi: null,
  rol_netligi: null,
  ucuncu_taraf_onayi: null,
  gerekce_metni: null,
  ...degisiklik,
});

describe("kanitAdresi", () => {
  it("şemasız linke https ekler, şemalıyı korur", () => {
    expect(kanitAdresi("github.com/elif/x")).toBe("https://github.com/elif/x");
    expect(kanitAdresi("//github.com/x")).toBe("https://github.com/x");
    expect(kanitAdresi("http://ornek.org")).toBe("http://ornek.org");
  });
});

describe("kanitLinkleri", () => {
  it("yalnızca adresi olan link parçalarını, sırasıyla verir", () => {
    const linkler = kanitLinkleri([
      { id: "1", tur: "link", url: "a.org" },
      { id: "2", tur: "dosya", url: null },
      { id: "3", tur: "link", url: "b.org" },
    ]);
    expect(linkler.map((p) => p.url)).toEqual(["a.org", "b.org"]);
  });
});

describe("degerlendirildiMi", () => {
  it("gösterge yoksa ya da yalnızca referans doluysa hayır", () => {
    expect(degerlendirildiMi(null)).toBe(false);
    expect(degerlendirildiMi(skor({ ucuncu_taraf_onayi: 3 }))).toBe(false);
  });

  it("kanıt, sonuç ya da rolden biri doluysa evet (0 da bir sonuçtur)", () => {
    expect(degerlendirildiMi(skor({ kanit_orijinalligi: 0 }))).toBe(true);
    expect(degerlendirildiMi(skor({ rol_netligi: 2 }))).toBe(true);
  });
});

describe("kayitliCiktiTaslagi", () => {
  it("önizlemede ilk link gösterilir", () => {
    const cikti: SomutCiktiYaniti = {
      id: "c",
      baslik: "Kütüphane",
      aciklama: null,
      kanitlar: [
        { id: "1", tur: "link", url: "ilk.org" },
        { id: "2", tur: "link", url: "ikinci.org" },
      ],
      guven_skoru: null,
    };
    expect(kayitliCiktiTaslagi(cikti).kanit_linki).toBe("ilk.org");
    expect(
      kayitliCiktiTaslagi({ ...cikti, kanitlar: [] }).kanit_linki,
    ).toBeNull();
  });
});
