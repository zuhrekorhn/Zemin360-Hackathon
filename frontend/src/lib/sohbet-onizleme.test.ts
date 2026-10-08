import { describe, expect, it } from "vitest";

import type { FirmaKartiTaslagi, IhtiyacTaslagi } from "@/lib/api";
import {
  firmaKartiToplananlari,
  ihtiyacToplananlari,
} from "@/lib/sohbet-onizleme";

const ihtiyac = (ek: Partial<IhtiyacTaslagi> = {}): IhtiyacTaslagi => ({
  problem_tanimi: null,
  basari_kriteri: null,
  kisitlar: null,
  sehir_tercihi: null,
  calisma_modeli: null,
  musaitlik_tercihi: null,
  ...ek,
});

const tamamlar = (liste: { anahtar: string; tamam: boolean }[]) =>
  liste.filter((b) => b.tamam).map((b) => b.anahtar);

describe("ihtiyacToplananlari", () => {
  it("taslak yokken hiçbir şey tamam değil; zorunlular problem ve ölçüt", () => {
    const liste = ihtiyacToplananlari(null, false);
    expect(tamamlar(liste)).toEqual([]);
    expect(liste.filter((b) => !b.istegeBagli).map((b) => b.anahtar)).toEqual([
      "problem",
      "kriter",
    ]);
  });

  it("dolu alanları işaretler; hedef başarı ölçütünün hedef değerinden", () => {
    const liste = ihtiyacToplananlari(
      ihtiyac({
        problem_tanimi: "Kayıtlar kâğıtta.",
        basari_kriteri: "Rapor 10 dakikada çıksın.",
        basari_olcutu: { hedef_deger: "10 dakika" },
      }),
      false,
    );
    expect(tamamlar(liste)).toEqual(["problem", "kriter", "hedef"]);
  });

  it("iş birliği türü yalnızca ortak ilanında sorulur", () => {
    expect(
      ihtiyacToplananlari(null, false).map((b) => b.anahtar),
    ).not.toContain("isbirligi");
    const ortak = ihtiyacToplananlari(
      ihtiyac({ isbirligi_turu: "deneme_isi" }),
      true,
    );
    expect(tamamlar(ortak)).toEqual(["isbirligi"]);
  });
});

describe("firmaKartiToplananlari", () => {
  const taslak = (ek: Partial<FirmaKartiTaslagi> = {}): FirmaKartiTaslagi => ({
    ne_yapiyoruz: null,
    yetkinlikler: [],
    onceki_isler: null,
    aranan_isbirligi: null,
    isbirligi_turleri: [],
    ...ek,
  });

  it("zorunlular ne yapıldığı ve yetkinlikler", () => {
    const liste = firmaKartiToplananlari(null);
    expect(liste.filter((b) => !b.istegeBagli).map((b) => b.anahtar)).toEqual([
      "ne",
      "yetkinlik",
    ]);
  });

  it("boş yetkinlik listesi tamam sayılmaz", () => {
    expect(
      tamamlar(
        firmaKartiToplananlari(
          taslak({ ne_yapiyoruz: "Gıda bankası işletiyoruz." }),
        ),
      ),
    ).toEqual(["ne"]);
    expect(
      tamamlar(firmaKartiToplananlari(taslak({ yetkinlikler: ["lojistik"] }))),
    ).toEqual(["yetkinlik"]);
  });
});
