import { describe, expect, it } from "vitest";

import {
  KAPANMA_NEDENLERI,
  KAPILAR,
  arananEtiketi,
  arananParametresi,
  ilanKapali,
  ilanlariSirala,
} from "@/lib/ilan";

describe("KAPANMA_NEDENLERI", () => {
  it("backend'deki dört neden, sabit sırada", () => {
    expect(KAPANMA_NEDENLERI.map((n) => n.deger)).toEqual([
      "platformda_bulundu",
      "baska_yoldan_bulundu",
      "vazgecildi",
      "hatali_girildi",
    ]);
  });
});

describe("ilanlariSirala", () => {
  it("açıklar önce, kapalılar sonda; grup içi sıra korunur", () => {
    const ilanlar = [
      { id: "a", durum: "kapandi" },
      { id: "b", durum: "acik" },
      { id: "c", durum: "kapandi" },
      { id: "d", durum: "acik" },
    ];
    expect(ilanlariSirala(ilanlar).map((i) => i.id)).toEqual([
      "b",
      "d",
      "a",
      "c",
    ]);
  });

  it("ilanKapali", () => {
    expect(ilanKapali({ durum: "kapandi" })).toBe(true);
    expect(ilanKapali({ durum: "acik" })).toBe(false);
  });
});

describe("iki kapı", () => {
  it("parametre: yalnızca 'firma' ortak kapısı", () => {
    expect(arananParametresi("firma")).toBe("firma");
    expect(arananParametresi(null)).toBe("genc");
    expect(arananParametresi("herkes")).toBe("genc");
  });

  it("kapılar tanımlama sayfasına açık parametreyle gider (parametresiz adres kapı sorar)", () => {
    expect(KAPILAR.map((k) => [k.aranan, k.yol])).toEqual([
      ["genc", "/tanimlama?aranan=genc"],
      ["firma", "/tanimlama?aranan=firma"],
    ]);
  });

  it("etiket yalnızca ortak ilanında", () => {
    expect(arananEtiketi("firma")).toBe("İş birliği ortağı");
    expect(arananEtiketi("genc")).toBeNull();
  });
});
